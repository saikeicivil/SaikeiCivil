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
Saikei Civil - IFC Relationship Manager
Manages IFC relationships (IfcRelNests, IfcRelAggregates, etc.) and their Blender representation

This module provides utilities for querying and managing IFC relationship entities,
making it easy to navigate and modify the IFC spatial/logical structure.
"""

import ifcopenshell
import ifcopenshell.guid

from .logging_config import get_logger

logger = get_logger(__name__)


class IfcRelationshipManager:
    """
    Manages IFC relationships and provides query/update utilities.
    
    Handles:
    - IfcRelAggregates (spatial decomposition)
    - IfcRelNests (logical composition) 
    - IfcRelContainedInSpatialStructure (spatial containment)
    """
    
    @classmethod
    def get_parent(cls, ifc_entity, rel_type="IfcRelAggregates"):
        """
        Get the parent of an IFC entity through a relationship.
        
        Args:
            ifc_entity: The child entity to find parent of
            rel_type: Type of relationship ("IfcRelAggregates", "IfcRelNests", etc.)
            
        Returns:
            Parent IFC entity or None if not found
            
        Example:
            >>> road = ifc.by_type("IfcRoad")[0]
            >>> site = IfcRelationshipManager.get_parent(road)
            >>> print(site.Name)  # "Site"
        """
        from .native_ifc_manager import NativeIfcManager
        ifc = NativeIfcManager.get_file()
        
        if not ifc:
            return None
        
        # Find relationship where entity is in RelatedObjects
        for rel in ifc.by_type(rel_type):
            if ifc_entity in rel.RelatedObjects:
                return rel.RelatingObject
        
        return None
    
    @classmethod
    def get_children(cls, ifc_entity, rel_type="IfcRelAggregates"):
        """
        Get children of an IFC entity through a relationship.
        
        Args:
            ifc_entity: The parent entity to get children of
            rel_type: Type of relationship
            
        Returns:
            List of child IFC entities (ordered list for IfcRelNests)
            
        Example:
            >>> alignment = ifc.by_type("IfcAlignment")[0]
            >>> children = IfcRelationshipManager.get_children(alignment, "IfcRelNests")
            >>> print(children[0].is_a())  # "IfcAlignmentHorizontal"
        """
        from .native_ifc_manager import NativeIfcManager
        ifc = NativeIfcManager.get_file()
        
        if not ifc:
            return []
        
        # Find relationship where entity is RelatingObject
        for rel in ifc.by_type(rel_type):
            if rel.RelatingObject == ifc_entity:
                return list(rel.RelatedObjects)
        
        return []
    
    @classmethod
    def get_relationship(cls, parent, child, rel_type="IfcRelAggregates"):
        """
        Get the relationship entity between parent and child.
        
        Args:
            parent: Parent IFC entity
            child: Child IFC entity
            rel_type: Type of relationship
            
        Returns:
            IfcRel* entity or None if relationship doesn't exist
            
        Example:
            >>> rel = IfcRelationshipManager.get_relationship(site, road)
            >>> print(rel.GlobalId)
        """
        from .native_ifc_manager import NativeIfcManager
        ifc = NativeIfcManager.get_file()
        
        if not ifc:
            return None
        
        for rel in ifc.by_type(rel_type):
            if (rel.RelatingObject == parent and 
                child in rel.RelatedObjects):
                return rel
        
        return None
    
    @classmethod
    def add_child(cls, parent, child, rel_type="IfcRelAggregates", name=None):
        """
        Add a child to a parent through a relationship.
        Creates new relationship if one doesn't exist, or adds to existing.
        
        Args:
            parent: Parent IFC entity
            child: Child IFC entity to add
            rel_type: Type of relationship to create
            name: Optional name for the relationship
            
        Returns:
            The IfcRel* entity (new or existing)
            
        Example:
            >>> new_road = ifc.create_entity("IfcRoad", ...)
            >>> IfcRelationshipManager.add_child(site, new_road)
        """
        from .native_ifc_manager import NativeIfcManager
        ifc = NativeIfcManager.get_file()
        
        if not ifc:
            raise ValueError("No IFC file loaded")
        
        # Check if relationship already exists for this parent
        existing_rel = None
        for rel in ifc.by_type(rel_type):
            if rel.RelatingObject == parent:
                existing_rel = rel
                break
        
        if existing_rel:
            # Add to existing relationship
            related = list(existing_rel.RelatedObjects)
            if child not in related:
                related.append(child)
                existing_rel.RelatedObjects = related
            return existing_rel
        else:
            # Create new relationship
            new_rel = ifc.create_entity(
                rel_type,
                GlobalId=ifcopenshell.guid.new(),
                Name=name or f"{parent.is_a()}Contains{child.is_a()}",
                RelatingObject=parent,
                RelatedObjects=[child]
            )
            return new_rel
    
    @classmethod
    def remove_child(cls, parent, child, rel_type="IfcRelAggregates"):
        """
        Remove a child from a parent relationship.
        Deletes relationship if no children remain.
        
        Args:
            parent: Parent IFC entity
            child: Child IFC entity to remove
            rel_type: Type of relationship
            
        Returns:
            True if removed, False if relationship not found
            
        Example:
            >>> IfcRelationshipManager.remove_child(site, old_road)
        """
        from .native_ifc_manager import NativeIfcManager
        ifc = NativeIfcManager.get_file()
        
        if not ifc:
            return False
        
        for rel in ifc.by_type(rel_type):
            if rel.RelatingObject == parent:
                related = list(rel.RelatedObjects)
                if child in related:
                    related.remove(child)
                    
                    if related:
                        # Update relationship with remaining children
                        rel.RelatedObjects = related
                    else:
                        # Remove relationship if no children left
                        ifc.remove(rel)
                    
                    return True
        
        return False
    
    @classmethod
    def move_entity(cls, entity, old_parent, new_parent, rel_type="IfcRelAggregates"):
        """
        Move an entity from one parent to another.
        
        Args:
            entity: The entity to move
            old_parent: Current parent entity
            new_parent: New parent entity
            rel_type: Type of relationship
            
        Returns:
            True if successful
            
        Example:
            >>> # Move road from site_a to site_b
            >>> IfcRelationshipManager.move_entity(road, site_a, site_b)
        """
        # Remove from old parent
        removed = cls.remove_child(old_parent, entity, rel_type)
        
        # Add to new parent
        if removed:
            cls.add_child(new_parent, entity, rel_type)
            return True
        
        return False
    
    @classmethod
    def get_all_descendants(cls, ifc_entity, rel_type="IfcRelAggregates"):
        """
        Recursively get all descendants of an entity.
        
        Args:
            ifc_entity: Parent entity
            rel_type: Type of relationship to follow
            
        Returns:
            List of all descendant entities (depth-first order)
            
        Example:
            >>> project = ifc.by_type("IfcProject")[0]
            >>> all_entities = IfcRelationshipManager.get_all_descendants(project)
            >>> print(f"Total entities under project: {len(all_entities)}")
        """
        descendants = []
        children = cls.get_children(ifc_entity, rel_type)
        
        for child in children:
            descendants.append(child)
            # Recursively get descendants of this child
            descendants.extend(cls.get_all_descendants(child, rel_type))
        
        return descendants
    
    @classmethod
    def get_spatial_container(cls, ifc_entity):
        """
        Get the spatial container for an entity.
        Uses IfcRelContainedInSpatialStructure.
        
        Args:
            ifc_entity: The entity to find container for
            
        Returns:
            Spatial container (IfcSite, IfcBuilding, etc.) or None
            
        Example:
            >>> alignment = ifc.by_type("IfcAlignment")[0]
            >>> site = IfcRelationshipManager.get_spatial_container(alignment)
            >>> print(site.Name)  # "Site"
        """
        from .native_ifc_manager import NativeIfcManager
        ifc = NativeIfcManager.get_file()
        
        if not ifc:
            return None
        
        for rel in ifc.by_type("IfcRelContainedInSpatialStructure"):
            if ifc_entity in rel.RelatedElements:
                return rel.RelatingStructure
        
        return None
    
    @classmethod
    def set_spatial_container(cls, element, container):
        """
        Place an element in a spatial container.
        Creates or updates IfcRelContainedInSpatialStructure.
        
        Args:
            element: Element to contain (IfcElement, IfcAlignment, etc.)
            container: Spatial container (IfcSite, IfcBuilding, etc.)
            
        Returns:
            The IfcRelContainedInSpatialStructure entity
            
        Example:
            >>> alignment = ifc.create_entity("IfcAlignment", ...)
            >>> site = ifc.by_type("IfcSite")[0]
            >>> IfcRelationshipManager.set_spatial_container(alignment, site)
        """
        from .native_ifc_manager import NativeIfcManager
        ifc = NativeIfcManager.get_file()
        
        if not ifc:
            raise ValueError("No IFC file loaded")
        
        # Check if already contained in this or another container
        existing_rel = None
        for rel in ifc.by_type("IfcRelContainedInSpatialStructure"):
            if element in rel.RelatedElements:
                # Already contained somewhere
                if rel.RelatingStructure == container:
                    # Already in correct container
                    return rel
                else:
                    # Remove from old container
                    elements = list(rel.RelatedElements)
                    elements.remove(element)
                    if elements:
                        rel.RelatedElements = elements
                    else:
                        ifc.remove(rel)
                break
        
        # Find or create relationship for new container
        for rel in ifc.by_type("IfcRelContainedInSpatialStructure"):
            if rel.RelatingStructure == container:
                existing_rel = rel
                break
        
        if existing_rel:
            # Add to existing relationship
            elements = list(existing_rel.RelatedElements)
            if element not in elements:
                elements.append(element)
                existing_rel.RelatedElements = elements
            return existing_rel
        else:
            # Create new relationship
            new_rel = ifc.create_entity(
                "IfcRelContainedInSpatialStructure",
                GlobalId=ifcopenshell.guid.new(),
                Name=f"{container.is_a()}Contains{element.is_a()}",
                RelatingStructure=container,
                RelatedElements=[element]
            )
            return new_rel
    
    @classmethod
    def visualize_relationships(cls, ifc_entity, indent=0):
        """
        Print relationship tree for an entity (for debugging).

        Args:
            ifc_entity: Entity to visualize relationships for
            indent: Indentation level (used for recursion)

        Example:
            >>> project = ifc.by_type("IfcProject")[0]
            >>> IfcRelationshipManager.visualize_relationships(project)
        """
        prefix = "  " * indent
        logger.debug("%s┌─ %s '%s'", prefix, ifc_entity.is_a(), ifc_entity.Name)

        # Show parent relationships
        parent_agg = cls.get_parent(ifc_entity, "IfcRelAggregates")
        if parent_agg and indent == 0:
            logger.debug("%s│  ↑ Aggregated by: %s '%s'", prefix, parent_agg.is_a(), parent_agg.Name)

        parent_nest = cls.get_parent(ifc_entity, "IfcRelNests")
        if parent_nest and indent == 0:
            logger.debug("%s│  ↑ Nested in: %s '%s'", prefix, parent_nest.is_a(), parent_nest.Name)

        # Show spatial container
        container = cls.get_spatial_container(ifc_entity)
        if container and indent == 0:
            logger.debug("%s│  📍 Contained in: %s '%s'", prefix, container.is_a(), container.Name)

        # Show children (Aggregates)
        children_agg = cls.get_children(ifc_entity, "IfcRelAggregates")
        if children_agg:
            logger.debug("%s│", prefix)
            logger.debug("%s├─ Aggregates:", prefix)
            for child in children_agg:
                cls.visualize_relationships(child, indent + 1)

        # Show children (Nests)
        children_nest = cls.get_children(ifc_entity, "IfcRelNests")
        if children_nest:
            logger.debug("%s│", prefix)
            logger.debug("%s├─ Nests:", prefix)
            for i, child in enumerate(children_nest):
                logger.debug("%s│  [%s] %s '%s'", prefix, i, child.is_a(), getattr(child, 'Name', 'N/A'))

        if indent == 0:
            logger.debug("%s└─%s", prefix, "─"*50)
    
    @classmethod
    def validate_spatial_structure(cls):
        """
        Validate the spatial structure of the IFC file.
        Checks for common issues and prints report.

        Returns:
            dict with validation results

        Example:
            >>> results = IfcRelationshipManager.validate_spatial_structure()
            >>> if not results['valid']:
            >>>     print(f"Errors: {results['errors']}")
        """
        from .native_ifc_manager import NativeIfcManager
        ifc = NativeIfcManager.get_file()

        if not ifc:
            return {'valid': False, 'errors': ['No IFC file loaded']}

        errors = []
        warnings = []

        logger.info("\n%s", "="*60)
        logger.info("VALIDATING IFC SPATIAL STRUCTURE")
        logger.info("%s", "="*60)

        # Check for IfcProject
        projects = ifc.by_type("IfcProject")
        if not projects:
            errors.append("No IfcProject found")
        elif len(projects) > 1:
            warnings.append(f"Multiple IfcProject entities found ({len(projects)})")
        else:
            project = projects[0]
            logger.info("✓ Project: %s", project.Name)

            # Check Project → Site
            sites = cls.get_children(project, "IfcRelAggregates")
            if not sites:
                errors.append("Project has no Sites")
            else:
                logger.info("✓ Sites: %s", len(sites))

                for site in sites:
                    # Check Site → Facilities
                    facilities = cls.get_children(site, "IfcRelAggregates")
                    logger.info("  ✓ Site '%s' has %s facilities", site.Name, len(facilities))

                    # Check for alignments in site
                    alignments = ifc.by_type("IfcAlignment")
                    site_alignments = [a for a in alignments
                                      if cls.get_spatial_container(a) == site]
                    logger.info("    ✓ %s alignments in site", len(site_alignments))

        # Check for orphaned entities
        all_entities = ifc.by_type("IfcRoot")
        orphans = []
        for entity in all_entities:
            if entity.is_a() in ["IfcProject"]:
                continue  # Project is root

            # Check if entity has parent or container
            has_parent = (cls.get_parent(entity, "IfcRelAggregates") is not None or
                         cls.get_parent(entity, "IfcRelNests") is not None or
                         cls.get_spatial_container(entity) is not None)

            if not has_parent:
                orphans.append(entity)

        if orphans:
            warnings.append(f"{len(orphans)} orphaned entities found")
            logger.warning("\n⚠ Orphaned entities:")
            for orphan in orphans[:5]:  # Show first 5
                logger.warning("    - %s '%s'", orphan.is_a(), getattr(orphan, 'Name', 'N/A'))
            if len(orphans) > 5:
                logger.warning("    ... and %s more", len(orphans) - 5)

        logger.info("\n%s", "="*60)
        if errors:
            logger.error("❌ VALIDATION FAILED")
            for error in errors:
                logger.error("  ❌ %s", error)
        else:
            logger.info("✅ VALIDATION PASSED")

        if warnings:
            logger.warning("\nWarnings:")
            for warning in warnings:
                logger.warning("  ⚠ %s", warning)

        logger.info("%s\n", "="*60)

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


# =============================================================================
# Utility Functions
# =============================================================================

def get_alignment_segments(alignment):
    """
    Get all segments of an alignment in order.
    
    Args:
        alignment: IfcAlignment entity
        
    Returns:
        List of IfcAlignmentSegment entities (in order)
    """
    # Get horizontal layout
    horizontals = IfcRelationshipManager.get_children(alignment, "IfcRelNests")
    if not horizontals:
        return []
    
    horizontal = horizontals[0]  # Assume first is horizontal
    
    # Get segments (in order!)
    segments = IfcRelationshipManager.get_children(horizontal, "IfcRelNests")
    return segments


def print_alignment_structure(alignment):
    """
    Print the complete structure of an alignment for debugging.

    Args:
        alignment: IfcAlignment entity
    """
    logger.debug("\n%s", "="*60)
    logger.debug("ALIGNMENT STRUCTURE: %s", alignment.Name)
    logger.debug("%s", "="*60)

    segments = get_alignment_segments(alignment)

    logger.debug("Total Segments: %s", len(segments))
    logger.debug("\nSegments:")

    station = 0.0
    for i, seg in enumerate(segments):
        params = seg.DesignParameters
        length = params.SegmentLength
        seg_type = params.PredefinedType

        logger.debug("  [%s] Station %8.2f: %s %8.2fm", i, station, seg_type, length)
        station += length

    logger.debug("\nTotal Length: %.2fm", station)
    logger.debug("%s\n", "="*60)


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    """
    Example usage of IfcRelationshipManager.
    Run this after creating an IFC file with spatial structure.
    """
    
    from .native_ifc_manager import NativeIfcManager
    
    # Get IFC file
    ifc = NativeIfcManager.get_file()
    
    if ifc:
        # Validate structure
        results = IfcRelationshipManager.validate_spatial_structure()
        
        # Visualize project structure
        project = ifc.by_type("IfcProject")[0]
        IfcRelationshipManager.visualize_relationships(project)
        
        # Show alignment structures
        alignments = ifc.by_type("IfcAlignment")
        for alignment in alignments:
            print_alignment_structure(alignment)
