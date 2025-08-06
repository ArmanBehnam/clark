from typing import Dict, List, Optional
import re


class ExtractionPatterns:

    def __init__(self):
        self.patterns = self._load_default_patterns()

    def _load_default_patterns(self) -> Dict[str, List[str]]:
        return {
            'building_codes': self._get_building_code_patterns(),
            'material_specs': self._get_material_spec_patterns(),
            'project_info': self._get_project_info_patterns(),
            'dimensions': self._get_dimension_patterns(),
            'load_requirements': self._get_load_patterns(),
            'structural_steel': self._get_structural_steel_patterns(),
            'abbreviations': self._get_abbreviation_patterns()
        }

    def _get_building_code_patterns(self) -> List[str]:
        return [
            # Primary building codes (CDES relevant)
            r'(?:IBC|International Building Code)\s*(\d{4})',
            r'(?:OBC|Ohio Building Code)\s*(\d{4})',
            r'(?:CBC|California Building Code)\s*(\d{4})',
            r'(?:FBC|Florida Building Code)\s*(\d{4})',
            r'(?:BCNYS|Building Code of New York State)\s*(\d{4})',
            r'(?:NYCBC|New York City Building Code)\s*(\d{4})',
            r'(?:Chicago Building Code)\s*(\d{4})',
            r'(?:EBC|Epcot Building Code|RCID|Reedy Creek Improvement District)\s*(\d{4})',
            r'(?:MSBC|Massachusetts State Building Code)\s*(?:(\d+)(?:th|st|nd|rd)\s*edition)',

            # ASCE Standards (CDES relevant)
            r'(?:ASCE|American Society of Civil Engineers)\s*7[-\s]*(\d{2})',
            r'ASCE\s*7[-\s]*(?:05|10|16|22)',

            # Key technical standards (CDES relevant)
            r'(?:AISI|American Iron)\s*(\d{4})',
            r'(?:ASTM|Association Society for Testing)\s*([A-Z]\s*\d+)',
            r'ASTM\s*(?:C754|C645|A1003)',
            r'(?:AWS|American Welding Society)\s*(D\d+\.\d+)',
            r'AWS\s*D1\.3',

            # DoD blast design (CDES relevant)
            r'(?:UFC|Unified Facilities Criteria)\s*(4-010-0[12])',
            r'DoD\s*(?:Minimum\s*)?(?:Antiterrorism|Standards)'

            # Note: TMS, NFPA, NEC, ANSI, IECC, IFGC excluded per CDES requirements
        ]

    def _get_material_spec_patterns(self) -> List[str]:
        return [
            # Gauge/Thickness (CDES core need)
            r'(\d+)\s*(?:ga|gauge|gage|mils)\b',
            r'(\d+(?:\.\d+)?)\s*(?:inch|in\.?|")\s*thick',
            r'Thickness[:\s]*(\d+(?:\.\d+)?)\s*(?:inch|in\.?|mm)',
            r'(\d+)\s*mil(?:s)?\b',  # 1/1000 of an inch

            # Grade specifications (CDES core need)
            r'Grade\s*(\d+)',  # Grade 50 = 50 ksi, Grade 33 = 33 ksi
            r'(?:A36|grade\s*36)\s*ksi',
            r'(?:A992|GR50|grade\s*50)',

            # ASTM Standards (CDES relevant)
            r'ASTM\s*([A-Z]\s*\d+(?:[/-][A-Z]?\d+)*)',

            # Steel Types (CDES relevant)
            r'Type\s*([A-Z]?\d+[A-Z]*)',
            r'Class\s*([A-Z0-9]+)',
            # Note: Temper excluded per CDES requirements

            # Material Properties (CDES core need)
            r'(?:Yield\s*Strength|Tensile\s*Strength)[:\s]*(\d+(?:\.\d+)?)\s*(?:ksi|MPa)',
            r'(\d+)\s*ksi\s*(?:yield|material)',

            # Concrete (CDES relevant)
            r'(\d+)\s*psi\s*(?:concrete|compressive)',
            r'(?:Normal|Light)\s*weight\s*concrete',

            # Metal Deck (CDES relevant)
            r'(?:Roof|Floor)\s*deck[:\s]*(\d+(?:\.\d+)?)["\s]*x\s*(\d+)\s*ga',
            r'(\d+-\d+/\d+)["\s]*x\s*(\d+)\s*ga',  # 1-1/2" x 22 ga format

            # Member Nomenclature (CDES core need)
            r'(?:Stud|Track|Joist|Rafter|Header|Sill|Jamb|Lintel)',

            # Finishes (CDES relevant)
            r'(?:Galvanized|Hot-dip\s*galvanized)',
            r'Zinc\s*coating\s*(G\d+)'
        ]

    def _get_dimension_patterns(self) -> List[str]:
        return [
            # Imperial format (XX'-XX")
            r"(\d+)'-(\d+(?:\.\d+)?)\"",
            r"(\d+(?:\.\d+)?)'\s*(?:x|\*|by)\s*(\d+(?:\.\d+)?)'",
            r'(\d+(?:\.\d+)?)\s*(?:SF|sq\.?\s*ft\.?)',

            # Decimal feet (XX.XX')
            r"(\d+\.\d+)'",

            # On center spacing
            r'(\d+(?:\.\d+)?)["\s]*o\.?c\.?',
            r'(\d+(?:\.\d+)?)\s*(?:inches?|in\.?|")\s*(?:on\s*center|o\.c\.)',

            # Elevation references
            r'Elevation[:\s]*(\d+(?:\.\d+)?)',
            r'(?:AFF|Above\s*finished\s*floor)[:\s]*(\d+(?:\.\d+)?)',
            r'(?:TOS|T/Steel|Top\s*of\s*steel)[:\s]*(\d+(?:\.\d+)?)',
            r'(?:BOS|Bottom\s*of\s*steel)[:\s]*(\d+(?:\.\d+)?)',
            r'(?:JBE|Joist\s*bearing\s*elevation)[:\s]*(\d+(?:\.\d+)?)',

            # Building dimensions
            r'Building\s*(?:Height|Area)[:\s]*([^\n]+)',
            r'(?:Height|Width|Length|Depth|Diameter|Radius)[:\s]*(\d+(?:\.\d+)?)\s*(?:ft|feet|\'|in|")',
            r'(?:Clear\s*(?:Height|Span)|Span)[:\s]*(\d+(?:\.\d+)?)\s*(?:ft|feet|\')',

            # Member spacing
            r'(\d+(?:\.\d+)?)\s*(?:inches?|in\.?|")\s*O\.?C\.?'
        ]

    def _get_load_patterns(self) -> List[str]:
        return [
            # Basic load values (should match your abbreviations)
            r'PSF\s+POUNDS\s+PER\s+SQUARE\s+FOOT',
            r'PSI\s+POUNDS\s+PER\s+SQUARE\s+INCH',
            r'KSI\s+KIPS\s+PER\s+SQUARE\s+INCH',
            r'KLF\s+KIPS\s+PER\s+LINEAR\s+FOOT',
            r'KSF\s+KIPS\s+PER\s+SQUARE\s+FOOT',

            # Numerical load values
            r'(\d+(?:\.\d+)?)\s*(?:psf|PSF|kPa|psi|ksi|MPa)',
            r'(\d+(?:\.\d+)?)\s*(?:lb|lbs|kN|plf|PLF|kN/m)',

            # Load specifications
            r'(?:Dead|Live|Wind|Snow|Seismic)\s*Load[:\s]*(\d+(?:\.\d+)?)\s*(?:psf|PSF)',
            r'Basic\s*Wind\s*Speed[:\s]*(\d+)\s*mph',

            # Deflection criteria
            r'L\s*/\s*(240|360|480|600|720)',
            r'(?:Wall|Roof|Floor)\s*deflection[:\s]*L\s*/\s*(\d+)',
        ]

    def _get_structural_steel_patterns(self) -> List[str]:
        return [
            # Cold-formed steel terminology
            r'(?:CFMF|CFF|Cold-formed\s*(?:metal\s*)?framing)',
            r'STRUCTURAL\s*STEEL',
            r'STEEL\s*(?:DECKING|DECK|TRUSS)',
            r'COLD-FORMED\s*METAL\s*FRAMING',

            # Steel member sizes (from AISC manual)
            r'W\s*(\d+)\s*[xX]\s*(\d+)',  # Wide flange: W14 x 30
            r'L\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+/\d+)',  # Angle: L 2 x 2 x 3/8
            r'C\s*(\d+)\s*[xX]\s*(\d+)',  # Channel: C15 x 50
            r'HSS\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+/\d+)',  # HSS 6 x 6 x 1/2

            # AWS Welding
            r'AWS\s+(D\d+\.\d+)',
            r'E\s*(\d+[xX]?)',

            # AISC References
            r'AISC["\s]*([^"\n]+)',

            # Steel Grades
            r'ASTM\s*A(\d+)',
            r'(?:A36|A992|GR50|Grade\s*(?:36|50))',

            # Member types
            r'(?:Stud|Track|Joist|Rafter|Parapet|Partition)',
            r'(?:Purlin|Girt)',  # PEMB members
            r'(?:Shear\s*Wall|shearwall|X-bracing)',
            r'(?:Header|Sill|Jamb|Lintel)',

            # Angles and orientations
            r'(?:LLV|Long\s*leg\s*vertical)',
            r'(?:LLH|Long\s*leg\s*horizontal)'
        ]

    def _get_fire_protection_patterns(self) -> List[str]:
        return [
            # Fire ratings (1 hour, 2 hour, etc.)
            r'(?:Fire\s*(?:rating|resistance)|Fire\s*separation)[:\s]*(\d+)\s*hour',
            r'(\d+)\s*(?:hour|hr)\s*(?:fire\s*)?(?:rating|resistance)',

            # Sprinkler systems
            r'(?:Sprinkler|NFPA\s*13)',

            # Items marked as not relevant but included for completeness
            r'(?:Fire\s*alarm|Fire\s*extinguisher)',
            r'NFPA\s*(\d+)',

            # Fire protection assemblies
            r'(?:Fire\s*(?:door|wall|barrier|damper))',
            r'(?:Smoke\s*(?:detector|detection))',
            r'(?:Exit\s*(?:sign|light)|Emergency\s*light)'
        ]

    def _get_abbreviation_patterns(self) -> List[str]:
        return [
            # Elevation references
            r'(?:TOS|T/Steel|Top\s*of\s*steel)',
            r'(?:BOS|Bottom\s*of\s*steel)',
            r'(?:JBE|Joist\s*bearing\s*elevation)',
            r'(?:AFF|Above\s*finished\s*floor)',
            r'(?:T/Parapet|T\.O\.\s*Parapet|Top\s*of\s*parapet)',
            r'(?:B/Deck|Bottom\s*of\s*deck)',
            r'(?:T/Joist|Top\s*of\s*joist)',

            # Angle orientations
            r'(?:LLV|Long\s*leg\s*vertical)',
            r'(?:LLH|Long\s*leg\s*horizontal)',

            # General abbreviations
            r'(?:HSS|Hollow\s*structural\s*section)',
            r'(?:CFMF|CFF|Cold-formed\s*(?:metal\s*)?framing)',
            r'(?:CMU|Concrete\s*masonry\s*unit)',
            r'(?:UNO|Unless\s*noted\s*otherwise)',
            r'(?:VIF|Verify\s*in\s*field)',
            r'(?:RTU|Roof\s*top\s*unit)',

            # Drawing types
            r'(?:Section|Elevation|Plan)\s*(?:\d+|[A-Z]+)',
            r'(?:Building|Wall|Roof|Floor)\s*(?:section|elevation|plan)'
        ]

    def _get_project_info_patterns(self) -> List[str]:
        return [
            # Basic project information (CDES relevant)
            r'Project[:\s]+([^\n]+)',
            r'(?:Location|Address)[:\s]+([^\n]+)',
            r'Date[:\s]+([^\n]+)',

            # Professional contacts (CDES relevant)
            r'(?:Architect\s*of\s*Record|Architect)[:\s]*([^\n]+)',
            r'(?:Structural\s*Engineer\s*of\s*Record|Structural\s*Engineer|Engineer)[:\s]*([^\n]+)',
            r'Owner[:\s]*([^\n]+)',

            # Drawing information (CDES relevant)
            r'(?:Drawing|Sheet)\s*(?:Number|No\.?)[:\s]*([^\n]+)',
            r'Sheet[:\s]*(\d+)\s*of\s*(\d+)',
            r'Scale[:\s]*([^\n]+)',
            r'(?:Project|Job)\s*Number[:\s]*([^\n]+)',
            r'Revision[:\s]*([^\n]+)'

        ]


    def _get_structural_steel_patterns(self) -> List[str]:
        return [
            # Cold-formed steel terminology (CDES core need)
            r'(?:CFMF|CFF|Cold-formed\s*(?:metal\s*)?framing)',
            r'STRUCTURAL\s*STEEL',
            r'STEEL\s*(?:DECKING|DECK|TRUSS)',
            r'COLD-FORMED\s*METAL\s*FRAMING',

            # Steel member sizes from AISC manual (CDES relevant)
            r'W\s*(\d+)\s*[xX]\s*(\d+)',  # Wide flange: W14 x 30
            r'L\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+/\d+)',  # Angle: L 2 x 2 x 3/8
            r'C\s*(\d+)\s*[xX]\s*(\d+)',  # Channel: C15 x 50
            r'HSS\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+/\d+)',  # HSS 6 x 6 x 1/2

            # AWS Welding (CDES relevant)
            r'AWS\s+(D\d+\.\d+)',
            r'E\s*(\d+[xX]?)',

            # AISC References (CDES relevant)
            r'AISC["\s]*([^"\n]+)',

            # Steel Grades (CDES core need)
            r'ASTM\s*A(\d+)',
            r'(?:A36|A992|GR50|Grade\s*(?:36|50))',

            # Member types (CDES core need)
            r'(?:Stud|Track|Joist|Rafter|Parapet|Partition)',
            r'(?:Purlin|Girt)',  # PEMB members
            r'(?:Shear\s*Wall|shearwall|X-bracing)',
            r'(?:Header|Sill|Jamb|Lintel)',

            # Angles and orientations (CDES relevant)
            r'(?:LLV|Long\s*leg\s*vertical)',
            r'(?:LLH|Long\s*leg\s*horizontal)'
        ]
    
    def get_patterns(self, category: str = None) -> Dict[str, List[str]]:
        if category:
            return {category: self.patterns.get(category, [])}
        return self.patterns.copy()
    
    def add_pattern(self, category: str, pattern: str) -> None:
        if category not in self.patterns:
            self.patterns[category] = []
        self.patterns[category].append(pattern)
    
    def remove_pattern(self, category: str, pattern: str) -> bool:
        if category in self.patterns and pattern in self.patterns[category]:
            self.patterns[category].remove(pattern)
            return True
        return False
    
    def validate_pattern(self, pattern: str) -> bool:
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False
    
    def get_categories(self) -> List[str]:
        return list(self.patterns.keys())
    
    def get_pattern_count(self, category: str = None) -> int:
        if category:
            return len(self.patterns.get(category, []))
        return sum(len(patterns) for patterns in self.patterns.values())



_extraction_patterns: Optional[ExtractionPatterns] = None


def get_patterns() -> ExtractionPatterns:
    global _extraction_patterns
    if _extraction_patterns is None:
        _extraction_patterns = ExtractionPatterns()
    return _extraction_patterns


def reset_patterns() -> None:
    global _extraction_patterns
    _extraction_patterns = None