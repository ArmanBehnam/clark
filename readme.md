# PDF Processor v2.1 - Modular Document Processing Engine
A comprehensive, modular document processing system designed specifically for engineering and construction documents. Combines multiple OCR engines, computer vision, and pattern recognition to convert PDF documents into structured, searchable data.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the interactive interface
python main.py
```

## Core Architecture

```
PDF Input → Pipeline Orchestrator → Structured Output
    ↓              ↓                      ↓
 File Validation → Processing Stages → Export Formats
                    ├─ PDF Text Extraction
                    ├─ Multi-Engine OCR  
                    ├─ Table Detection
                    ├─ Pattern Matching
                    ├─ Spatial Analysis
                    └─ Classification
```


## Core Components

### Modular Architecture

```
pdf_processor/
├── core/           # Data models, interfaces, exceptions
├── config/         # Settings and extraction patterns  
├── ocr/           # Multiple OCR engine implementations
├── processors/    # Image, pattern, spatial processing
├── extractors/    # PDF text and table extraction
├── stages/        # Processing pipeline stages
├── evaluation/    # Quality metrics and assessment
├── exporters/     # Output format handlers
└── utils/         # Logging, file operations
```




### Data Models

**ExtractedElement**: Text/table/image with spatial coordinates

**ExtractionResult**: Complete document processing output


### Stage Details

**1. PDF Text Extraction**
- pdfplumber for machine-readable text
- Table extraction from PDF structure
- Page metadata collection

**2. OCR Processing** 
- Multi-engine text extraction with fallbacks
- Image enhancement (contrast, noise reduction)
- Confidence-based result selection

**3. Table Detection**
- Computer vision line detection
- Grid pattern recognition  
- Spatial table reconstruction

**4. Pattern Matching**
- 80+ regex patterns across 9 categories
- Engineering-specific terminology
- Contextual data extraction

**5. Spatial Analysis**
- Element grouping and layout analysis
- Text region clustering
- Coverage metrics calculation



### Document Classification

- **Architectural Plans**: Floor plans, elevations, sections
- **Construction Specs**: CSI format specifications  
- **Engineering Design**: Structural calculations, drawings
- **Building Codes**: Regulatory documents
- **Fire Protection**: Safety system specifications
- **Material Specs**: Product data sheets



The structure of the files are
```
OCR/
├── main.py                 # Interactive CLI interface
├── config/
│   ├── settings.py         # Configuration management
│   └── patterns.py         # Extraction patterns (80+ patterns)
├── core/
│   ├── models.py          # Data models and enums
│   ├── interfaces.py      # Abstract base classes
│   └── exceptions.py      # Custom exception hierarchy
├── ocr_engine/
│   ├── base.py           # OCR engine registry and management
│   ├── aws_textract.py   # AWS Textract integration
│   ├── azure.py          # Azure Document Intelligence
│   ├── mistral.py        # Mistral AI OCR
│   ├── tesseract.py      # Tesseract OCR wrapper
│   └── opencv.py         # OpenCV text detection
├── processors/
│   ├── image.py          # Image enhancement and table detection
│   ├── pattern.py        # Pattern extraction engine
│   ├── spatial_analyzer.py # Layout and spatial analysis
│   └── document_classifier.py # Document type classification
├── extractors/
│   ├── pdf_extractor.py  # PDF text and metadata extraction
│   └── table_extractor.py # Table structure extraction
├── stages/
│   └── base.py           # Processing pipeline stages
├── exporters/
│   └── json_exporter.py  # JSON output formatting
├── utils/
│   ├── help.py           # Main processor classes
│   └── logging_utils.py  # Logging configuration
├── requirements.txt       # Python dependencies
└── readme.md             # This file
```

## Features

### Interactive Menu System
- **Full Document Processing**: Complete analysis with OCR, tables, and patterns
- **Phase 1 Processing**: Enhanced keyword-based filtering with fallback extraction
- **Specialized Extraction**: OCR-only, table-only, or pattern-only processing
- **Batch Processing**: Process multiple documents automatically
- **System Validation**: Configuration and engine availability checking

### Multi-Engine OCR Support
- **AWS Textract** (Primary) - Cloud-based document analysis
- **Azure Document Intelligence** - Microsoft's OCR service
- **Mistral OCR** - AI-powered text extraction
- **Tesseract** - Open-source OCR engine
- **OpenCV** - Computer vision-based text detection

### Advanced Processing Capabilities
- **Intelligent Fallback**: Automatic engine switching on failure
- **Image Enhancement**: Contrast, noise reduction, scaling
- **Table Detection**: Computer vision-based table extraction
- **Pattern Recognition**: 80+ regex patterns across 20+ categories
- **Spatial Analysis**: Layout analysis and element grouping
- **Document Classification**: Automatic document type detection

### Enhanced Processing Features
- **Keyword Filtering**: Target specific sections (e.g., "STRUCTURAL STEEL NOTES")
- **Custom Keywords**: Add domain-specific search terms
- **Fallback Extraction**: Full-text extraction when keywords not found
- **Page-Level Results**: Detailed per-page analysis and metrics

## Quality Assessment

### Comprehensive Metrics

**Text Accuracy**
- **CER** (Character Error Rate): Industry standard <2% excellent
- **WER** (Word Error Rate): <5% excellent performance  
- **BLEU Score**: Similarity to reference text
- **ROUGE-L**: Longest common subsequence accuracy

**Spatial Accuracy**
- **IoU@0.5/0.75**: Bounding box intersection thresholds
- **Mean IoU**: Average spatial accuracy
- **Coverage Analysis**: Percentage of page processed

**Domain-Specific Accuracy**
- **Technical Terminology**: Engineering term recognition
- **Field-Level Accuracy**: Category-specific extraction success
- **Pattern Match Rate**: Structured data extraction efficiency


## Output Formats

### 1. Raw Extraction (complete data)
```json
{
  "document_id": "uuid",
  "filename": "document.pdf", 
  "total_pages": 110,
  "extracted_text": "full document text...",
  "structured_data": {
    "building_codes": ["IBC 2024", "NFPA 13"],
    "material_specs": ["Steel Grade A36", "16 ga"],
    "dimensions": ["2400 SF", "12 ft x 20 ft"]
  },
  "tables": [...],
  "elements": [...],
  "confidence": 0.84
}
```

### 2. Structured Format (cleaned data)
```json
{
  "document_metadata": {
    "id": "uuid",
    "document_type": "construction_specification"
  },
  "extracted_data_tables": {
    "building_codes": [
      {"value": "IBC 2024", "confidence": 0.8, "source": "regex_pattern"}
    ]
  },
  "quality_metrics": {
    "ocr_elements": 6354065,
    "tables_found": 1789,
    "patterns_matched": 45
  }
}
```

## Research Foundation

Based on comprehensive analysis of:
- **OCR Evaluation**: Character/Word Error Rates, BLEU/ROUGE adaptation
- **Computer Vision**: Spatial IoU metrics, layout analysis
- **Document AI**: End-to-end processing, domain adaptation
- **Engineering Standards**: Technical terminology, industry patterns

## References & Inspiration

1. **buddyd16/Structural-Engineering**  
   URL: https://github.com/buddyd16/Structural-Engineering  
   IBC 2012 implementation and structural calculations

2. **gpyocr**  
   URL: https://github.com/sinecode/gpyocr  
   Python OCR wrapper concepts

3. **Novel Contributions**
   - Multi-engine OCR with intelligent fallbacks
   - Engineering-specific pattern recognition
   - Comprehensive spatial analysis
   - Modular, extensible architecture
   - Production-ready quality assessment