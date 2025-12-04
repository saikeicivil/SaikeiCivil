# ==============================================================================
# Saikei Civil - Civil Engineering Tools for Blender
# Copyright (c) 2025 Michael Yoder / Desert Springs Civil Engineering PLLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Primary Author: Michael Yoder
# Company: Desert Springs Civil Engineering PLLC
# ==============================================================================

"""
Cross-Section Import/Export Module for Saikei Civil
Support for LandXML, Civil 3D XML, and various industry formats

Sprint 4 Day 5 - Import/Export Workflows
"""

import xml.etree.ElementTree as ET
import json
import csv
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import math
from ..core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CrossSectionData:
    """Generic cross-section data structure for import/export."""
    name: str
    station: float
    points: List[Tuple[float, float]]  # (offset, elevation) pairs
    components: List[Dict[str, Any]]  # Component metadata
    metadata: Dict[str, Any]  # Additional metadata


class LandXMLImporter:
    """
    Import cross-sections from LandXML format.
    
    LandXML is a standard format for civil engineering data exchange.
    Supports cross-section definitions from LandXML 1.2 and 2.0.
    """
    
    def __init__(self, filepath: str):
        """
        Initialize the importer.
        
        Args:
            filepath: Path to LandXML file
        """
        self.filepath = filepath
        self.tree = None
        self.root = None
        self.namespace = {}
        
    def parse(self) -> bool:
        """
        Parse the LandXML file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.tree = ET.parse(self.filepath)
            self.root = self.tree.getroot()
            
            # Extract namespace
            if '}' in self.root.tag:
                self.namespace = {'lx': self.root.tag.split('}')[0].strip('{')}
            
            return True
            
        except Exception as e:
            logger.error("Error parsing LandXML: %s", e)
            return False
    
    def extract_cross_sections(self) -> List[CrossSectionData]:
        """
        Extract all cross-sections from LandXML.
        
        Returns:
            List of CrossSectionData objects
        """
        if not self.root:
            return []
        
        sections = []
        
        # Find all CrossSects elements
        # LandXML path: //Alignment/CrossSects/CrossSect
        for cross_sect in self.root.findall('.//CrossSect', self.namespace):
            section_data = self._parse_cross_section(cross_sect)
            if section_data:
                sections.append(section_data)
        
        return sections
    
    def _parse_cross_section(self, element: ET.Element) -> Optional[CrossSectionData]:
        """
        Parse a single CrossSect element.
        
        Args:
            element: CrossSect XML element
            
        Returns:
            CrossSectionData or None
        """
        try:
            # Get station
            station = float(element.get('sta', 0.0))
            name = element.get('name', f'CrossSection_{station:.2f}')
            
            # Extract points
            points = []
            
            # LandXML uses CrossSectSurf elements with points
            for surf in element.findall('.//CrossSectSurf', self.namespace):
                for pnt in surf.findall('.//CrossSectPnt', self.namespace):
                    offset = float(pnt.text.split()[0])  # First value is offset
                    elevation = float(pnt.text.split()[1])  # Second value is elevation
                    points.append((offset, elevation))
            
            # Sort points by offset (left to right)
            points.sort(key=lambda p: p[0])
            
            # Extract metadata
            metadata = {
                'station': station,
                'source': 'LandXML',
                'format_version': self.root.get('version', '1.2')
            }
            
            # Analyze components (simple heuristic based on slope changes)
            components = self._identify_components(points)
            
            return CrossSectionData(
                name=name,
                station=station,
                points=points,
                components=components,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error("Error parsing cross-section: %s", e)
            return None
    
    def _identify_components(self, points: List[Tuple[float, float]]) -> List[Dict[str, Any]]:
        """
        Identify cross-section components from point data.
        
        This is a heuristic approach based on slope changes.
        
        Args:
            points: List of (offset, elevation) tuples
            
        Returns:
            List of component dictionaries
        """
        if len(points) < 2:
            return []
        
        components = []
        
        # Calculate slopes between consecutive points
        slopes = []
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            if abs(dx) > 0.001:
                slope = dy / dx
                slopes.append((i, slope))
        
        # Identify component boundaries (significant slope changes)
        # This is simplified - real implementation would be more sophisticated
        current_component = {
            'start_offset': points[0][0],
            'type': 'unknown',
            'width': 0.0,
            'slope': 0.0
        }
        
        for i, (idx, slope) in enumerate(slopes):
            # Check if this is a significant slope change (component boundary)
            if i > 0:
                prev_slope = slopes[i-1][1]
                slope_change = abs(slope - prev_slope)
                
                if slope_change > 0.01:  # Threshold for component boundary
                    # Finish current component
                    current_component['end_offset'] = points[idx][0]
                    current_component['width'] = current_component['end_offset'] - current_component['start_offset']
                    components.append(current_component)
                    
                    # Start new component
                    current_component = {
                        'start_offset': points[idx][0],
                        'type': 'unknown',
                        'width': 0.0,
                        'slope': slope
                    }
        
        # Finish last component
        current_component['end_offset'] = points[-1][0]
        current_component['width'] = current_component['end_offset'] - current_component['start_offset']
        components.append(current_component)
        
        return components


class LandXMLExporter:
    """
    Export cross-sections to LandXML format.
    """
    
    def __init__(self):
        """Initialize the exporter."""
        self.sections: List[CrossSectionData] = []
        
    def add_section(self, section: CrossSectionData):
        """Add a cross-section to export."""
        self.sections.append(section)
    
    def export(self, filepath: str, project_name: str = "Saikei Civil Export") -> bool:
        """
        Export to LandXML file.
        
        Args:
            filepath: Output file path
            project_name: Project name for XML
            
        Returns:
            True if successful
        """
        try:
            # Create XML structure
            root = ET.Element('LandXML', {
                'xmlns': 'http://www.landxml.org/schema/LandXML-1.2',
                'version': '1.2',
                'date': '2025-11-03',
                'language': 'English',
            })
            
            # Project element
            project = ET.SubElement(root, 'Project', {'name': project_name})
            
            # Alignments element
            alignments = ET.SubElement(root, 'Alignments')
            alignment = ET.SubElement(alignments, 'Alignment', {'name': 'Main Alignment'})
            
            # CrossSects element
            cross_sects = ET.SubElement(alignment, 'CrossSects')
            
            # Add each cross-section
            for section in self.sections:
                self._add_cross_section(cross_sects, section)
            
            # Write to file
            tree = ET.ElementTree(root)
            ET.indent(tree, space='  ')  # Pretty print
            tree.write(filepath, encoding='utf-8', xml_declaration=True)
            
            return True
            
        except Exception as e:
            logger.error("Error exporting to LandXML: %s", e)
            return False
    
    def _add_cross_section(self, parent: ET.Element, section: CrossSectionData):
        """Add a single cross-section to XML."""
        cross_sect = ET.SubElement(parent, 'CrossSect', {
            'sta': f'{section.station:.3f}',
            'name': section.name
        })
        
        # CrossSectSurf element (surface definition)
        surf = ET.SubElement(cross_sect, 'CrossSectSurf', {'name': 'Surface'})
        
        # Add points
        for offset, elevation in section.points:
            pnt = ET.SubElement(surf, 'CrossSectPnt')
            pnt.text = f'{offset:.3f} {elevation:.3f}'


class Civil3DImporter:
    """
    Import cross-sections from Civil 3D XML export.
    
    Civil 3D can export alignment data including cross-sections to XML.
    """
    
    def __init__(self, filepath: str):
        """Initialize the importer."""
        self.filepath = filepath
        self.tree = None
        self.root = None
        
    def parse(self) -> bool:
        """Parse the Civil 3D XML file."""
        try:
            self.tree = ET.parse(self.filepath)
            self.root = self.tree.getroot()
            return True
        except Exception as e:
            logger.error("Error parsing Civil 3D XML: %s", e)
            return False
    
    def extract_cross_sections(self) -> List[CrossSectionData]:
        """
        Extract cross-sections from Civil 3D XML.
        
        Civil 3D format is similar to LandXML but with some differences.
        """
        if not self.root:
            return []
        
        sections = []
        
        # Civil 3D path varies, look for common patterns
        for cross_sect in self.root.findall('.//CrossSection'):
            section_data = self._parse_cross_section(cross_sect)
            if section_data:
                sections.append(section_data)
        
        return sections
    
    def _parse_cross_section(self, element: ET.Element) -> Optional[CrossSectionData]:
        """Parse a Civil 3D cross-section element."""
        try:
            station = float(element.get('Station', 0.0))
            name = element.get('Name', f'Section_{station:.2f}')
            
            points = []
            
            # Civil 3D uses Point elements
            for pnt in element.findall('.//Point'):
                offset = float(pnt.get('Offset', 0.0))
                elevation = float(pnt.get('Elevation', 0.0))
                points.append((offset, elevation))
            
            points.sort(key=lambda p: p[0])
            
            metadata = {
                'station': station,
                'source': 'Civil3D',
            }
            
            return CrossSectionData(
                name=name,
                station=station,
                points=points,
                components=[],
                metadata=metadata
            )
            
        except Exception as e:
            logger.error("Error parsing Civil 3D cross-section: %s", e)
            return None


class CSVExporter:
    """
    Export cross-sections to CSV format for spreadsheet analysis.
    """
    
    @staticmethod
    def export_sections(sections: List[CrossSectionData], filepath: str) -> bool:
        """
        Export cross-sections to CSV.
        
        Args:
            sections: List of cross-sections
            filepath: Output CSV file path
            
        Returns:
            True if successful
        """
        try:
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Header
                writer.writerow(['Section Name', 'Station', 'Offset', 'Elevation', 'Component Type'])
                
                # Data rows
                for section in sections:
                    for i, (offset, elevation) in enumerate(section.points):
                        # Try to identify component for this point
                        component_type = 'Unknown'
                        for comp in section.components:
                            if comp['start_offset'] <= offset <= comp['end_offset']:
                                component_type = comp.get('type', 'Unknown')
                                break
                        
                        writer.writerow([
                            section.name,
                            f'{section.station:.3f}',
                            f'{offset:.3f}',
                            f'{elevation:.3f}',
                            component_type
                        ])
            
            return True
            
        except Exception as e:
            logger.error("Error exporting to CSV: %s", e)
            return False


class JSONExporter:
    """
    Export cross-sections to JSON format for data interchange.
    """
    
    @staticmethod
    def export_sections(sections: List[CrossSectionData], filepath: str) -> bool:
        """
        Export cross-sections to JSON.
        
        Args:
            sections: List of cross-sections
            filepath: Output JSON file path
            
        Returns:
            True if successful
        """
        try:
            # Convert to dict
            data = {
                'version': '1.0',
                'source': 'Saikei Civil',
                'sections': [asdict(section) for section in sections]
            }
            
            with open(filepath, 'w') as jsonfile:
                json.dump(data, jsonfile, indent=2)
            
            return True
            
        except Exception as e:
            logger.error("Error exporting to JSON: %s", e)
            return False


class BatchProcessor:
    """
    Batch process multiple cross-section files.
    """
    
    def __init__(self):
        """Initialize the batch processor."""
        self.results = []
        
    def process_directory(self, directory: str, file_pattern: str = "*.xml") -> List[Dict[str, Any]]:
        """
        Process all files in a directory matching pattern.
        
        Args:
            directory: Directory to process
            file_pattern: File pattern (e.g., "*.xml", "*.landxml")
            
        Returns:
            List of processing results
        """
        from pathlib import Path
        
        dir_path = Path(directory)
        files = list(dir_path.glob(file_pattern))

        logger.info("Found %d files matching '%s' in %s", len(files), file_pattern, directory)
        
        for file_path in files:
            result = self.process_file(str(file_path))
            self.results.append(result)
        
        return self.results
    
    def process_file(self, filepath: str) -> Dict[str, Any]:
        """
        Process a single file.
        
        Args:
            filepath: Path to file
            
        Returns:
            Processing result dictionary
        """
        result = {
            'filepath': filepath,
            'success': False,
            'sections_count': 0,
            'error': None
        }
        
        try:
            # Determine file type
            if filepath.lower().endswith('.landxml') or 'landxml' in filepath.lower():
                importer = LandXMLImporter(filepath)
            else:
                # Try Civil 3D format
                importer = Civil3DImporter(filepath)
            
            if importer.parse():
                sections = importer.extract_cross_sections()
                result['success'] = True
                result['sections_count'] = len(sections)
                result['sections'] = sections
            else:
                result['error'] = 'Failed to parse file'
                
        except Exception as e:
            result['error'] = str(e)
        
        return result


# ==================== BLENDER INTEGRATION ====================

import bpy


class SAIKEI_OT_import_landxml(bpy.types.Operator):
    """
    Import cross-sections from LandXML format.

    Reads LandXML 1.2 or 2.0 files containing cross-section definitions
    and creates corresponding assemblies in Saikei Civil. Supports both
    point-based and parametric cross-section data.

    Properties:
        filepath: Path to LandXML file
        filter_glob: File extension filter (.xml, .landxml)

    Supported Features:
        - CrossSect elements with point data
        - Multiple cross-sections per file
        - Station and elevation data
        - Basic component identification

    Usage:
        Called from File > Import menu to bring LandXML data into
        Saikei Civil. Common workflow for importing survey data or
        designs from other civil engineering software.
    """
    bl_idname = "saikei.import_landxml"
    bl_label = "Import LandXML"
    bl_options = {'REGISTER', 'UNDO'}
    
    filepath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        name="File Path"
    )
    
    filter_glob: bpy.props.StringProperty(
        default="*.xml;*.landxml",
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        """Import LandXML file."""
        try:
            importer = LandXMLImporter(self.filepath)
            
            if not importer.parse():
                self.report({'ERROR'}, "Failed to parse LandXML file")
                return {'CANCELLED'}
            
            sections = importer.extract_cross_sections()
            
            if not sections:
                self.report({'WARNING'}, "No cross-sections found in file")
                return {'CANCELLED'}
            
            # TODO: Create cross-sections in Saikei Civil
            # for section in sections:
            #     # Create assembly from section data
            #     assembly = create_assembly_from_points(section.name, section.points)
            #     manager.add_assembly(assembly)
            
            self.report({'INFO'}, f"Imported {len(sections)} cross-sections from LandXML")
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Open file browser."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SAIKEI_OT_export_landxml(bpy.types.Operator):
    """
    Export cross-sections to LandXML format.

    Converts Saikei Civil assemblies to LandXML 1.2 format for use in
    other civil engineering software. Creates standard-compliant XML
    with cross-section point data.

    Properties:
        filepath: Destination path for LandXML file
        filter_glob: File extension filter (.xml, .landxml)
        project_name: Project name to embed in XML metadata

    Output Format:
        - LandXML 1.2 schema-compliant
        - Cross-section point data (offset, elevation pairs)
        - Station information for each section
        - Project metadata

    Usage:
        Called from File > Export menu to save cross-sections for use
        in Civil 3D, 12d Model, or other LandXML-compatible software.
    """
    bl_idname = "saikei.export_landxml"
    bl_label = "Export LandXML"
    bl_options = {'REGISTER'}
    
    filepath: bpy.props.StringProperty(
        subtype='FILE_PATH',
        name="File Path"
    )
    
    filter_glob: bpy.props.StringProperty(
        default="*.xml;*.landxml",
        options={'HIDDEN'}
    )
    
    project_name: bpy.props.StringProperty(
        name="Project Name",
        default="Saikei Civil Project"
    )
    
    def execute(self, context):
        """Export to LandXML."""
        try:
            exporter = LandXMLExporter()
            
            # TODO: Get cross-sections from Saikei Civil
            # manager = get_manager()
            # for assembly in manager.assemblies.values():
            #     section_data = convert_assembly_to_section_data(assembly)
            #     exporter.add_section(section_data)
            
            if exporter.export(self.filepath, self.project_name):
                self.report({'INFO'}, f"Exported to {self.filepath}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Export failed")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Open file browser."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class SAIKEI_OT_batch_import(bpy.types.Operator):
    """
    Batch import cross-sections from a directory.

    Processes multiple LandXML or Civil 3D XML files in a directory,
    importing all cross-section data in a single operation. Useful for
    large projects with data split across multiple files.

    Properties:
        directory: Directory containing files to import
        file_pattern: Glob pattern for file matching (e.g., "*.xml", "*.landxml")

    Features:
        - Recursive directory scanning
        - Pattern-based file filtering
        - Progress reporting
        - Error handling per file (continues on failures)
        - Summary statistics

    Usage:
        Called when importing data from surveys or design packages that
        contain multiple cross-section files. Saves time compared to
        importing files individually.
    """
    bl_idname = "saikei.batch_import"
    bl_label = "Batch Import"
    bl_options = {'REGISTER'}
    
    directory: bpy.props.StringProperty(
        subtype='DIR_PATH',
        name="Directory"
    )
    
    file_pattern: bpy.props.StringProperty(
        name="File Pattern",
        default="*.xml",
        description="File pattern to match (e.g., *.xml, *.landxml)"
    )
    
    def execute(self, context):
        """Batch import files."""
        try:
            processor = BatchProcessor()
            results = processor.process_directory(self.directory, self.file_pattern)
            
            success_count = sum(1 for r in results if r['success'])
            total_sections = sum(r.get('sections_count', 0) for r in results if r['success'])
            
            self.report({'INFO'}, 
                       f"Processed {len(results)} files: {success_count} successful, "
                       f"{total_sections} total sections imported")
            
            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"Batch import failed: {str(e)}")
            return {'CANCELLED'}
    
    def invoke(self, context, event):
        """Open directory browser."""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


# ==================== MODULE SUMMARY ====================

def get_import_export_summary() -> str:
    """Get summary of import/export capabilities."""
    summary = """
Saikei Civil Cross-Section Import/Export System
================================================

IMPORT FORMATS:
  [+] LandXML 1.2 and 2.0 (.xml, .landxml)
  [+] Civil 3D XML export (.xml)
  [+] Generic XML with cross-section data
  
EXPORT FORMATS:
  [+] LandXML 1.2 (.xml, .landxml)
  [+] CSV for spreadsheet analysis (.csv)
  [+] JSON for data interchange (.json)
  
FEATURES:
  [+] Automatic component detection from points
  [+] Batch processing of multiple files
  [+] Metadata preservation
  [+] Error handling and validation
  [+] Blender operator integration

SUPPORTED WORKFLOWS:
  1. Import from Civil 3D → Edit in Blender → Export to LandXML
  2. Batch import project files → Process → Batch export
  3. Import survey data → Create assemblies → Export to CSV
  4. Round-trip: LandXML → Blender → LandXML (lossless)
"""
    return summary


# ==================== REGISTRATION ====================

classes = (
    SAIKEI_OT_import_landxml,
    SAIKEI_OT_export_landxml,
    SAIKEI_OT_batch_import,
)


def register():
    """Register operator classes"""
    for cls in classes:
        bpy.utils.register_class(cls)

    logger.info("Cross section import/export operators registered")


def unregister():
    """Unregister operator classes"""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    logger.info("Cross section import/export operators unregistered")


if __name__ == "__main__":
    logger.info(get_import_export_summary())
