# Georeferencing Deferral to Bonsai

## Strategy

When Bonsai is installed, Saikei should **NOT** show its own georeferencing UI. Instead:
1. Use Bonsai's georeferencing data (IfcMapConversion, IfcProjectedCRS)
2. Hide Saikei's georef panel when Bonsai is active
3. Only show Saikei's georef UI in standalone mode

## Implementation

### Create `saikei_civil/tool/georeference.py`

```python
"""
Georeference Tool - Defers to Bonsai when available.
"""

import bpy
from typing import Optional, Tuple
from saikei_civil.tool.ifc import Ifc


class Georeference:
    """
    Georeferencing access - uses Bonsai's implementation when available.
    """
    
    @staticmethod
    def is_bonsai_georef_available() -> bool:
        """Check if Bonsai's georeferencing is available and configured."""
        if not Ifc.is_bonsai_mode():
            return False
        
        ifc = Ifc.get()
        if not ifc:
            return False
        
        # Check if georeferencing entities exist
        return len(ifc.by_type("IfcMapConversion")) > 0
    
    @staticmethod
    def has_georeferencing() -> bool:
        """Check if any georeferencing is configured (Bonsai or standalone)."""
        ifc = Ifc.get()
        if not ifc:
            return False
        return len(ifc.by_type("IfcMapConversion")) > 0
    
    @staticmethod
    def get_map_conversion():
        """Get the IfcMapConversion entity."""
        ifc = Ifc.get()
        if not ifc:
            return None
        conversions = ifc.by_type("IfcMapConversion")
        return conversions[0] if conversions else None
    
    @staticmethod
    def get_projected_crs():
        """Get the IfcProjectedCRS entity."""
        ifc = Ifc.get()
        if not ifc:
            return None
        crs_list = ifc.by_type("IfcProjectedCRS")
        return crs_list[0] if crs_list else None
    
    @staticmethod
    def get_crs_name() -> Optional[str]:
        """Get the CRS name (e.g., 'EPSG:6879')."""
        crs = Georeference.get_projected_crs()
        if crs:
            return crs.Name
        return None
    
    @staticmethod
    def get_eastings_northings_origin() -> Tuple[float, float, float]:
        """Get the origin point in projected coordinates."""
        conversion = Georeference.get_map_conversion()
        if conversion:
            return (
                conversion.Eastings or 0.0,
                conversion.Northings or 0.0,
                conversion.OrthogonalHeight or 0.0,
            )
        return (0.0, 0.0, 0.0)
    
    @staticmethod
    def transform_to_local(easting: float, northing: float, elevation: float = 0.0) -> Tuple[float, float, float]:
        """
        Transform global (projected) coordinates to local Blender coordinates.
        Uses Bonsai's transformation when available.
        """
        conversion = Georeference.get_map_conversion()
        if not conversion:
            return (easting, northing, elevation)
        
        # Get origin offset
        origin_e = conversion.Eastings or 0.0
        origin_n = conversion.Northings or 0.0
        origin_h = conversion.OrthogonalHeight or 0.0
        
        # Get rotation (XAxisAbscissa, XAxisOrdinate define rotation)
        x_abscissa = conversion.XAxisAbscissa or 1.0
        x_ordinate = conversion.XAxisOrdinate or 0.0
        
        # Apply transformation
        de = easting - origin_e
        dn = northing - origin_n
        dh = elevation - origin_h
        
        # Rotate to local
        import math
        angle = math.atan2(x_ordinate, x_abscissa)
        cos_a = math.cos(-angle)
        sin_a = math.sin(-angle)
        
        local_x = de * cos_a - dn * sin_a
        local_y = de * sin_a + dn * cos_a
        local_z = dh
        
        # Apply scale if present
        scale = conversion.Scale or 1.0
        local_x /= scale
        local_y /= scale
        
        return (local_x, local_y, local_z)
    
    @staticmethod
    def transform_to_global(x: float, y: float, z: float = 0.0) -> Tuple[float, float, float]:
        """
        Transform local Blender coordinates to global (projected) coordinates.
        """
        conversion = Georeference.get_map_conversion()
        if not conversion:
            return (x, y, z)
        
        # Get scale
        scale = conversion.Scale or 1.0
        scaled_x = x * scale
        scaled_y = y * scale
        
        # Get rotation
        x_abscissa = conversion.XAxisAbscissa or 1.0
        x_ordinate = conversion.XAxisOrdinate or 0.0
        
        import math
        angle = math.atan2(x_ordinate, x_abscissa)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        # Rotate to global
        global_de = scaled_x * cos_a - scaled_y * sin_a
        global_dn = scaled_x * sin_a + scaled_y * cos_a
        
        # Add origin offset
        origin_e = conversion.Eastings or 0.0
        origin_n = conversion.Northings or 0.0
        origin_h = conversion.OrthogonalHeight or 0.0
        
        easting = global_de + origin_e
        northing = global_dn + origin_n
        elevation = z + origin_h
        
        return (easting, northing, elevation)


# Convenience functions for direct import
def to_local(easting, northing, elevation=0.0):
    """Transform projected coords to local Blender coords."""
    return Georeference.transform_to_local(easting, northing, elevation)

def to_global(x, y, z=0.0):
    """Transform local Blender coords to projected coords."""
    return Georeference.transform_to_global(x, y, z)
```

---

### Create `saikei_civil/civil/module/georef/__init__.py`

```python
"""
Georeferencing Module - Defers to Bonsai when available.
"""

from . import prop
from . import ui

def register():
    prop.register()
    ui.register()

def unregister():
    ui.unregister()
    prop.unregister()
```

### Create `saikei_civil/civil/module/georef/prop.py`

```python
"""
Georeferencing Properties - Minimal, since we defer to Bonsai.
"""

import bpy
from bpy.types import PropertyGroup
from bpy.props import StringProperty, FloatProperty, BoolProperty, PointerProperty


class CivilGeorefProperties(PropertyGroup):
    """
    Georeferencing state - mostly for standalone mode.
    When Bonsai is active, this is informational only.
    """
    
    # Display properties (read from IFC)
    crs_name: StringProperty(
        name="CRS",
        description="Coordinate Reference System name",
        default="",
    )
    
    origin_easting: FloatProperty(
        name="Origin Easting",
        default=0.0,
    )
    
    origin_northing: FloatProperty(
        name="Origin Northing", 
        default=0.0,
    )
    
    # Standalone mode settings
    standalone_epsg: StringProperty(
        name="EPSG Code",
        description="EPSG code for standalone mode (e.g., 'EPSG:6879')",
        default="",
    )


def register():
    bpy.utils.register_class(CivilGeorefProperties)
    bpy.types.Scene.CivilGeorefProperties = PointerProperty(type=CivilGeorefProperties)


def unregister():
    del bpy.types.Scene.CivilGeorefProperties
    bpy.utils.unregister_class(CivilGeorefProperties)
```

### Create `saikei_civil/civil/module/georef/ui.py`

```python
"""
Georeferencing UI - Shows different content based on Bonsai availability.
"""

import bpy
from bpy.types import Panel
from saikei_civil.tool.ifc import Ifc
from saikei_civil.tool.georeference import Georeference


class CIVIL_PT_georeferencing(Panel):
    """Georeferencing panel - defers to Bonsai when available."""
    bl_label = "Georeferencing"
    bl_idname = "CIVIL_PT_georeferencing"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 101  # After main alignment panel
    
    @classmethod
    def poll(cls, context):
        return Ifc.has_file()
    
    def draw(self, context):
        layout = self.layout
        
        # Check if Bonsai is handling georeferencing
        if Ifc.is_bonsai_mode():
            self.draw_bonsai_mode(layout)
        else:
            self.draw_standalone_mode(context, layout)
    
    def draw_bonsai_mode(self, layout):
        """Show info when Bonsai is handling georeferencing."""
        box = layout.box()
        row = box.row()
        row.label(text="Bonsai Georeferencing Active", icon='CHECKMARK')
        
        # Show current georef info (read-only)
        if Georeference.has_georeferencing():
            col = box.column(align=True)
            
            crs_name = Georeference.get_crs_name()
            if crs_name:
                col.label(text=f"CRS: {crs_name}")
            
            origin = Georeference.get_eastings_northings_origin()
            col.label(text=f"Origin E: {origin[0]:.3f}")
            col.label(text=f"Origin N: {origin[1]:.3f}")
            col.label(text=f"Origin H: {origin[2]:.3f}")
        else:
            box.label(text="No georeferencing configured", icon='INFO')
        
        # Direct user to Bonsai's panel
        layout.separator()
        layout.label(text="Use Bonsai's Georeferencing panel to modify:")
        layout.label(text="Properties > Scene > Georeferencing", icon='RIGHTARROW')
    
    def draw_standalone_mode(self, context, layout):
        """Show full georef UI for standalone mode."""
        props = context.scene.CivilGeorefProperties
        
        layout.label(text="Standalone Mode", icon='FILE_3D')
        
        if Georeference.has_georeferencing():
            # Show current settings
            box = layout.box()
            box.label(text="Current Georeferencing:")
            
            crs_name = Georeference.get_crs_name()
            if crs_name:
                box.label(text=f"CRS: {crs_name}")
            
            origin = Georeference.get_eastings_northings_origin()
            col = box.column(align=True)
            col.label(text=f"Origin E: {origin[0]:.3f}")
            col.label(text=f"Origin N: {origin[1]:.3f}")
            
            layout.operator("civil.edit_georeferencing", text="Edit Georeferencing")
        else:
            # Setup new georeferencing
            layout.label(text="No georeferencing configured", icon='INFO')
            layout.prop(props, "standalone_epsg")
            layout.operator("civil.setup_georeferencing", text="Setup Georeferencing")


class CIVIL_PT_georef_quick(Panel):
    """Quick georef info in N-panel."""
    bl_label = "Georeferencing"
    bl_idname = "CIVIL_PT_georef_quick"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Saikei"
    bl_parent_id = "CIVIL_PT_alignment_quick"
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        if not Ifc.has_file():
            layout.label(text="No IFC file")
            return
        
        if Georeference.has_georeferencing():
            crs_name = Georeference.get_crs_name()
            layout.label(text=f"CRS: {crs_name or 'Unknown'}", icon='WORLD')
            
            if Ifc.is_bonsai_mode():
                layout.label(text="(via Bonsai)", icon='CHECKMARK')
        else:
            layout.label(text="Not georeferenced", icon='ERROR')


classes = (
    CIVIL_PT_georeferencing,
    CIVIL_PT_georef_quick,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
```

---

## Summary: Georeferencing Approach

| Scenario | Behavior |
|----------|----------|
| **Bonsai installed + georef configured** | Show read-only info, direct user to Bonsai's panel |
| **Bonsai installed + no georef** | Show message to use Bonsai's panel |
| **Standalone + georef exists** | Show editable Saikei UI |
| **Standalone + no georef** | Show Saikei setup wizard |

This approach:
1. **Avoids duplication** - Don't rebuild what Bonsai does well
2. **Maintains standalone capability** - Works without Bonsai
3. **Provides consistent data access** - `Georeference` class works in both modes
4. **Reduces maintenance burden** - Less code to maintain
