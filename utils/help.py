import os
import sys
import time
import uuid
import logging
from pathlib import Path
from typing import Union, Optional, Dict, Any, List
import numpy as np
import json
import time
from core.models import ExtractionResult, ProcessingMethod, DocumentType, ExtractedElement, SpatialTable, ImageInfo, ProcessingMetrics
from core.exceptions import PDFProcessorError, FileNotFoundError, UnsupportedFileTypeError, ProcessingError, ValidationError
from core.interfaces import ProcessingPipeline
from stages.base import PDFTextStage, OCRStage, TableStage, PatternStage, SpatialStage, ClassificationStage, FinalizationStage
from exporters.json_exporter import create_json_exporter

from config.settings import get_config, initialize_config
from ocr_engine.base import get_ocr_registry
from processors.image import create_image_processor
from processors.pattern import create_pattern_processor
from extractors.pdf_extractor import create_pdf_extractor
from processors.spatial_analyzer import create_spatial_analyzer
from processors.document_classifier import create_document_classifier
from utils.logging_utils import setup_logging

logger = logging.getLogger(__name__)


class PDFProcessor(ProcessingPipeline):

    def __init__(self, config_path: Optional[Path] = None):
        self.config = initialize_config(config_path)
        setup_logging(self.config.config.logging)
        self._initialize_components()
        self._stages = []
        self._setup_default_pipeline()
        logger.info("PDF Processor initialized successfully")

    def _initialize_components(self) -> None:
        try:
            self.ocr_registry = get_ocr_registry()
            self._register_ocr_engines()
            self.image_processor = create_image_processor()
            self.pattern_processor = create_pattern_processor()
            self.pdf_extractor = create_pdf_extractor()
            self.spatial_analyzer = create_spatial_analyzer()
            self.document_classifier = create_document_classifier()
            logger.info("All components initialized successfully")
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise PDFProcessorError(f"Failed to initialize components: {e}")

    def _register_ocr_engines(self) -> None:
        engines_to_register = []

        ocr_engines = [
            ('ocr_engine.aws_textract', 'create_aws_textract_engine'),
            ('ocr_engine.azure', 'create_azure_ocr_engine'),
            ('ocr_engine.claude', 'create_claude_ocr_engine'),
            # ('ocr_engine.mistral', 'create_mistral_ocr_engine'),
            ('ocr_engine.tesseract', 'create_tesseract_engine'),
            ('ocr_engine.opencv', 'create_opencv_engine')
        ]

        for module_name, function_name in ocr_engines:
            try:
                module = __import__(module_name, fromlist=[function_name])
                create_engine = getattr(module, function_name)
                engine = create_engine()
                engines_to_register.append(engine)
            except Exception as e:
                logger.warning(f"{module_name} not available: {e}")

        for engine in engines_to_register:
            self.ocr_registry.register(engine)

        available_engines = self.ocr_registry.get_available_engines()
        logger.info(f"Registered {len(available_engines)} OCR engines")

    def _setup_default_pipeline(self) -> None:

        self._stages = [
            PDFTextStage(self.pdf_extractor),
            OCRStage(self.ocr_registry, self.image_processor),
            # TableStage(self.table_extractor, self.image_processor),
            PatternStage(self.pattern_processor),
            SpatialStage(self.spatial_analyzer),
            ClassificationStage(self.document_classifier),
            FinalizationStage()
        ]

    def process(self, input_path: Path, **kwargs) -> ExtractionResult:
        input_path = Path(input_path)
        self._validate_input(input_path)

        document_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"Starting processing: {input_path.name} (ID: {document_id})")

        try:
            result = ExtractionResult(
                document_id=document_id,
                filename=input_path.name,
                total_pages=0,
                processing_method=ProcessingMethod.HYBRID
            )

            context = {
                'input_path': input_path,
                'result': result,
                'start_time': start_time,
                'config': self.config,
                **kwargs
            }

            for stage in self._stages:
                try:
                    logger.debug(f"Executing stage: {stage.name}")
                    stage_start = time.time()

                    if not stage.validate_input(context):
                        logger.warning(f"Stage {stage.name} input validation failed")
                        continue

                    context = stage.process(context)

                    stage_time = time.time() - stage_start
                    logger.debug(f"Stage {stage.name} completed in {stage_time:.2f}s")

                except Exception as e:
                    logger.error(f"Stage {stage.name} failed: {e}")
                    if stage.name in ['pdf_text', 'finalization']:
                        raise ProcessingError(stage.name, document_id, str(e))
                    else:
                        logger.warning(f"Continuing processing despite {stage.name} failure")
                        continue

            result = context['result']
            processing_time = time.time() - start_time
            result.processing_metrics.processing_time = processing_time
            result.confidence = self._calculate_overall_confidence(result)

            logger.info(f"Processing completed: {input_path.name} ({processing_time:.2f}s, confidence: {result.confidence:.2f})")
            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Processing failed for {input_path.name} after {processing_time:.2f}s: {e}")
            raise ProcessingError("pipeline", document_id, str(e))

    def _validate_input(self, input_path: Path) -> None:
        if not input_path.exists():
            raise FileNotFoundError(str(input_path))

        if not input_path.is_file():
            raise FileNotFoundError(f"Path is not a file: {input_path}")

        allowed_extensions = self.config.get('security.allowed_file_extensions', ['.pdf'])
        if input_path.suffix.lower() not in allowed_extensions:
            raise UnsupportedFileTypeError(str(input_path), input_path.suffix, allowed_extensions)

        max_size_mb = self.config.get('security.max_file_size_mb', 100)
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise ValidationError(f"File too large: {file_size_mb:.1f}MB (max: {max_size_mb}MB)")

    def _calculate_overall_confidence(self, result: ExtractionResult) -> float:
        if not result.elements:
            return 0.0

        element_confidences = [e.confidence for e in result.elements if e.confidence > 0]
        avg_element_confidence = sum(element_confidences) / len(element_confidences) if element_confidences else 0.0

        pattern_categories = len(result.structured_data)
        total_patterns = getattr(self.pattern_processor, '_compiled_patterns', {})
        total_patterns = len(total_patterns) if hasattr(total_patterns, '__len__') else 10
        pattern_score = min(pattern_categories / max(total_patterns * 0.2, 1), 1.0)

        table_score = min(len(result.tables) / 5, 1.0)
        text_length = len(result.extracted_text)
        coverage_score = min(text_length / 5000, 1.0)

        confidence = (avg_element_confidence * 0.4 + pattern_score * 0.3 + table_score * 0.2 + coverage_score * 0.1)
        return round(confidence, 3)

    def process_batch(self, input_dir: Path, output_dir: Path, file_pattern: str = "*.pdf", **kwargs) -> Dict[str, Any]:
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        output_dir.mkdir(parents=True, exist_ok=True)
        pdf_files = list(input_dir.glob(file_pattern))

        logger.info(f"Starting batch processing: {len(pdf_files)} files")

        results = {'total_files': len(pdf_files), 'successful': 0, 'failed': 0, 'results': [], 'errors': []}

        for pdf_file in pdf_files:
            try:
                logger.info(f"Processing batch file: {pdf_file.name}")
                result = self.process(pdf_file, **kwargs)
                output_file = output_dir / f"{pdf_file.stem}_result.json"
                self.save_result(result, output_file)

                results['successful'] += 1
                results['results'].append({
                    'file': pdf_file.name,
                    'status': 'success',
                    'output': output_file.name,
                    'confidence': result.confidence,
                    'pages': result.total_pages,
                    'elements': len(result.elements)
                })

            except Exception as e:
                logger.error(f"Batch processing failed for {pdf_file.name}: {e}")
                results['failed'] += 1
                results['errors'].append({'file': pdf_file.name, 'error': str(e)})

        logger.info(f"Batch processing completed: {results['successful']}/{len(pdf_files)} successful")
        return results

    def save_result(self, result: ExtractionResult, output_path: Path) -> None:
        exporter = create_json_exporter()
        exporter.export(result, output_path)
        logger.debug(f"Result saved to: {output_path}")

    def add_stage(self, stage, position: Optional[int] = None) -> None:
        if position is None:
            self._stages.append(stage)
        else:
            self._stages.insert(position, stage)
        logger.info(f"Added stage: {stage.name}")

    def remove_stage(self, stage_name: str) -> None:
        self._stages = [stage for stage in self._stages if stage.name != stage_name]
        logger.info(f"Removed stage: {stage_name}")

    def get_pipeline_info(self) -> Dict[str, Any]:
        return {
            'total_stages': len(self._stages),
            'stages': [
                {
                    'name': stage.name,
                    'dependencies': getattr(stage, 'dependencies', []),
                    'optional': getattr(stage, 'optional', False)
                }
                for stage in self._stages
            ]
        }

    def get_system_info(self) -> Dict[str, Any]:
        return {
            'processor_version': '2.0.0',
            'ocr_engines': self.ocr_registry.get_engine_info(),
            'available_stages': [stage.name for stage in self._stages],
            'component_status': {
                'image_processor': bool(self.image_processor),
                'pattern_processor': bool(self.pattern_processor),
                'pdf_extractor': bool(self.pdf_extractor),
                'table_extractor': bool(self.table_extractor),
                'spatial_analyzer': bool(self.spatial_analyzer),
                'document_classifier': bool(self.document_classifier)
            }
        }


class EnhancedPDFProcessor(PDFProcessor):

    def __init__(self, config_path: Optional[Path] = None):
        super().__init__(config_path)
        self.target_keywords = self._get_target_keywords()
        self.target_keywords = self._get_target_keywords()

    def _get_target_keywords(self) -> List[str]:
        return [
            'STRUCTURAL STEEL NOTES',
            'DESIGN CRITERIA',
            'GENERAL STRUCTURAL NOTES'
        ]

    def process_with_page_results(self, input_path: Path, **kwargs) -> Dict[str, Any]:
        input_path = Path(input_path)
        self._validate_input(input_path)

        document_id = str(uuid.uuid4())
        start_time = time.time()

        logger.info(f"Starting processing: {input_path.name} (ID: {document_id})")

        try:
            # Run normal processing
            result = self.process(input_path, **kwargs)

            # Generate page-level results
            page_results = self._generate_page_results(result)

            # Filter pages with target keywords
            filtered_pages = self._filter_pages_by_keywords(page_results)

            # FALLBACK: If no keywords found, extract all text from all pages
            if not filtered_pages:
                logger.info("No target keywords found. Extracting all text as fallback.")
                filtered_pages = self._extract_all_pages_as_fallback(page_results)

            # Create output
            enhanced_result = {
                'document_info': {
                    'document_id': document_id,
                    'filename': input_path.name,
                    'total_pages': result.total_pages,
                    'processing_time': time.time() - start_time,
                    'confidence': result.confidence,
                    'document_type': result.document_type.value if hasattr(result, 'document_type') else 'GENERAL'
                },
                'full_document_results': self._convert_result_to_dict(result),
                'page_level_results': page_results,
                'filtered_pages': {
                    'matching_pages': filtered_pages,
                    'total_matching_pages': len(filtered_pages),
                    'keywords_found': self._get_found_keywords(page_results) if filtered_pages else [],
                    'fallback_used': len(self._filter_pages_by_keywords(page_results)) == 0
                }
            }

            logger.info(f"Processing completed: {len(filtered_pages)} pages processed")
            return enhanced_result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Processing failed for {input_path.name} after {processing_time:.2f}s: {e}")
            # Fix: Use correct ProcessingError constructor
            raise ProcessingError("pipeline", document_id, str(e))

    def _generate_page_results(self, result: ExtractionResult) -> List[Dict[str, Any]]:
        page_results = []

        # Initialize page data structure
        pages_data = {}
        for page_num in range(1, result.total_pages + 1):
            pages_data[page_num] = {
                'page_number': page_num,
                'text_elements': [],
                'table_elements': [],
                'extracted_text': '',
                'structured_data': {},
                'element_count': 0,
                'confidence_avg': 0.0
            }

        # If result.extracted_text exists but no elements, use PDF text
        if result.extracted_text and not result.elements:
            text_chunks = self._split_text_by_pages(result.extracted_text, result.total_pages)
            for page_num, text_chunk in enumerate(text_chunks, 1):
                if page_num in pages_data:
                    pages_data[page_num]['extracted_text'] = text_chunk
                    pages_data[page_num]['element_count'] = 1
                    pages_data[page_num]['confidence_avg'] = 0.8

        # Organize elements by page
        for element in result.elements:
            page_num = element.page_number
            if page_num in pages_data:
                if element.element_type.value == 'table':
                    pages_data[page_num]['table_elements'].append({
                        'text': element.text,
                        'confidence': element.confidence,
                        'bbox': element.bbox.to_dict() if element.bbox else None,
                        'metadata': element.metadata
                    })
                else:
                    pages_data[page_num]['text_elements'].append({
                        'text': element.text,
                        'confidence': element.confidence,
                        'bbox': element.bbox.to_dict() if element.bbox else None,
                        'metadata': element.metadata
                    })

                pages_data[page_num]['extracted_text'] += element.text + ' '
                pages_data[page_num]['element_count'] += 1

        # Process each page
        for page_num, page_data in pages_data.items():
            # Calculate average confidence
            all_elements = page_data['text_elements'] + page_data['table_elements']
            if all_elements:
                page_data['confidence_avg'] = sum(elem['confidence'] for elem in all_elements) / len(all_elements)

            # Extract patterns with safety checks
            if page_data['extracted_text'] and page_data['extracted_text'].strip():
                try:
                    # Fix: Check if pattern_processor exists and handle None results
                    if hasattr(self, 'pattern_processor') and self.pattern_processor:
                        page_patterns = self.pattern_processor.extract_patterns(page_data['extracted_text'])
                        page_data['structured_data'] = page_patterns if page_patterns else {}
                    else:
                        page_data['structured_data'] = {}
                except Exception as e:
                    logger.warning(f"Pattern extraction failed for page {page_num}: {e}")
                    page_data['structured_data'] = {}
            else:
                page_data['structured_data'] = {}

            # Clean up text
            page_data['extracted_text'] = page_data['extracted_text'].strip()
            page_results.append(page_data)

        return page_results

    def _split_text_by_pages(self, full_text: str, total_pages: int) -> List[str]:
        """Roughly split text into page chunks"""
        if not full_text or total_pages <= 0:
            return [''] * total_pages

        chars_per_page = len(full_text) // total_pages
        chunks = []

        for i in range(total_pages):
            start = i * chars_per_page
            end = (i + 1) * chars_per_page if i < total_pages - 1 else len(full_text)
            chunks.append(full_text[start:end])

        return chunks

    def _extract_all_pages_as_fallback(self, page_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract all pages when no keywords are found"""
        fallback_pages = []

        for page_data in page_results:
            if page_data['extracted_text'].strip():
                page_data_copy = page_data.copy()
                page_data_copy['matched_keywords'] = []
                page_data_copy['keyword_count'] = 0
                page_data_copy['fallback_extraction'] = True
                fallback_pages.append(page_data_copy)

        return fallback_pages

    def _filter_pages_by_keywords(self, page_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered_pages = []

        for page_data in page_results:
            page_text = page_data['extracted_text'].upper()
            found_keywords = []

            for keyword in self.target_keywords:
                if keyword.upper() in page_text:
                    found_keywords.append(keyword)

            if found_keywords:
                page_data_copy = page_data.copy()
                page_data_copy['matched_keywords'] = found_keywords
                page_data_copy['keyword_count'] = len(found_keywords)
                page_data_copy['fallback_extraction'] = False
                filtered_pages.append(page_data_copy)

        return filtered_pages

    def _get_found_keywords(self, page_results: List[Dict[str, Any]]) -> List[str]:
        found_keywords = set()

        for page_data in page_results:
            page_text = page_data['extracted_text'].upper()
            for keyword in self.target_keywords:
                if keyword.upper() in page_text:
                    found_keywords.add(keyword)

        return list(found_keywords)

    def _convert_result_to_dict(self, result: ExtractionResult) -> Dict[str, Any]:
        """Convert ExtractionResult to dictionary with error handling"""
        try:
            return result.to_dict()
        except Exception as e:
            logger.warning(f"Failed to convert result to dict: {e}, using fallback")
            # Fallback conversion
            return {
                'document_id': getattr(result, 'document_id', ''),
                'filename': getattr(result, 'filename', ''),
                'total_pages': getattr(result, 'total_pages', 0),
                'extracted_text': getattr(result, 'extracted_text', ''),
                'elements': [
                    {
                        'text': elem.text,
                        'element_type': elem.element_type.value if hasattr(elem.element_type, 'value') else str(
                            elem.element_type),
                        'page_number': elem.page_number,
                        'confidence': elem.confidence,
                        'bbox': elem.bbox.to_dict() if elem.bbox and hasattr(elem.bbox, 'to_dict') else None,
                        'metadata': getattr(elem, 'metadata', {})
                    } for elem in getattr(result, 'elements', [])
                ],
                'tables': getattr(result, 'tables', []),
                'structured_data': getattr(result, 'structured_data', {}),
                'confidence': getattr(result, 'confidence', 0.0),
                'processing_method': result.processing_method.value if hasattr(result, 'processing_method') and hasattr(
                    result.processing_method, 'value') else 'HYBRID'
            }

    def add_custom_keywords(self, keywords: List[str]) -> None:
        self.target_keywords.extend(keywords)
        logger.info(f"Added {len(keywords)} custom keywords")

    def get_page_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        filtered_pages = result['filtered_pages']['matching_pages']
        is_fallback = result['filtered_pages'].get('fallback_used', False)
        total_pages = result['document_info']['total_pages']

        summary = {
            'total_pages': total_pages,
            'pages_processed': len(filtered_pages),
            'pages_with_keywords': len(filtered_pages),
            'percentage_with_keywords': (len(filtered_pages) / total_pages) * 100 if total_pages > 0 else 0,
            'extraction_method': 'keyword_filter' if not is_fallback else 'full_text_fallback',
            'percentage_processed': (len(filtered_pages) / total_pages) * 100 if total_pages > 0 else 0,
            'keywords_found': result['filtered_pages']['keywords_found'],
            'page_numbers_processed': [page['page_number'] for page in filtered_pages],
            'page_numbers_with_keywords': [page['page_number'] for page in filtered_pages],
            'average_confidence': sum(page['confidence_avg'] for page in filtered_pages) / len(
                filtered_pages) if filtered_pages else 0,
            'average_confidence_filtered_pages': sum(page['confidence_avg'] for page in filtered_pages) / len(
                filtered_pages) if filtered_pages else 0,
            'total_elements': sum(page['element_count'] for page in filtered_pages),
            'total_elements_in_filtered_pages': sum(page['element_count'] for page in filtered_pages)
        }

        return summary


