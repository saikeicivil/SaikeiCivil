# Saikei Civil - IFC-Native Civil Engineering for Blender

**A modern Blender extension for civil engineering design using IFC 4.3 (IFC4X3) standards.**

Saikei Civil brings professional-grade civil engineering tools directly into Blender, leveraging the power of IFC (Industry Foundation Classes) for data-driven infrastructure design.

---

## ✨ Features

### 🛣️ Horizontal Alignment Design

**Interactive PI-Based Workflow**
- Place Points of Intersection (PIs) directly in the 3D viewport
- Real-time alignment generation from PI positions
- Move PIs with Blender's G key - tangents and curves update instantly
- Full constraint-based design with automatic geometry updates

**Curve Insertion**
- Click any two adjacent tangent segments
- Specify curve radius
- Circular curves inserted automatically with proper civil engineering geometry
- Curves calculate PC (Point of Curvature) and PT (Point of Tangency) using standard formulas: `T = R × tan(Δ/2)`

**Live Updates**
- Depsgraph-based update system detects PI movement
- All segments (tangents and curves) regenerate in real-time
- No manual refresh needed - move a PI, see the entire alignment update instantly
- Compatible with BlenderBIM's transform tools

### 🏗️ IFC Spatial Hierarchy

**Full IFC4X3 Compliance**
- Proper spatial structure: `IfcProject → IfcSite → IfcRoad → IfcAlignment`
- All geometric elements are native IFC entities (`IfcAlignmentSegment`, etc.)
- Organizational empties for Alignments and Geomodels
- Blender Outliner hierarchy mirrors IFC structure via parenting

**BlenderBIM Integration**
- Fully compatible with BlenderBIM extension
- No conflicts with BlenderBIM's modal operators or transform systems
- Works alongside BlenderBIM for complete BIM workflows
- IFC entities properly linked and managed

### 🗺️ Georeferencing

- CRS (Coordinate Reference System) search and selection
- Project georeferencing with Map Conversion support
- IFC-native georeferencing entities (`IfcMapConversion`, `IfcProjectedCRS`)
- Integration with spatial reference systems

### 📐 Additional Tools

**Vertical Alignments**
- Vertical geometry management
- Grade and curve definitions
- IFC vertical alignment entities

**Cross Sections**
- Cross-section definition and management
- Import/export capabilities
- Template-based workflows

**File Management**
- Create new IFC files with proper hierarchy
- Open existing IFC files
- Save IFC to disk
- File information display (entity counts, schema version)

---

## 🚀 Installation

### Method 1: Symlink (Recommended for Development)

Run this command in **Command Prompt (Administrator)**:

```cmd
mklink /D "C:\Users\[YourUsername]\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\saikei_civil" "C:\Path\To\Saikei Civil\Saikei Civil_ext"
```

Replace `[YourUsername]` and `C:\Path\To\Saikei Civil` with your actual paths.

### Method 2: Direct Copy

Copy the entire `Saikei Civil_ext` folder to:
```
C:\Users\[YourUsername]\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\
```

### Enable the Extension

1. Restart Blender
2. Go to `Edit > Preferences > Get Extensions`
3. Find "Saikei Civil" in the list
4. Enable the extension

---

## 📖 Quick Start

### 1. Create a New IFC Project

1. Open the **Saikei Civil Panel** in the 3D Viewport sidebar (N key)
2. Go to **File Management** panel
3. Click **New IFC**
4. Your IFC spatial hierarchy is created automatically

### 2. Create Your First Alignment

1. Go to the **Alignment** panel
2. Click **Create Alignment**
3. Enter a name (e.g., "Main Road")
4. Click OK

### 3. Place PIs Interactively

1. In the Alignment panel, click **Add PI** (or use the dropdown for interactive mode)
2. Click in the 3D viewport to place Points of Intersection
3. Press ESC to finish placement
4. Tangent lines are generated automatically between PIs

### 4. Add Curves

1. In the Alignment panel, click **Add Curve**
2. Click on the **first tangent** segment
3. Click on the **second tangent** segment (must be adjacent)
4. Enter the **curve radius** in the dialog
5. Click OK - curve is inserted automatically!

### 5. Edit Your Alignment

1. Select any PI in the Outliner or 3D viewport
2. Press **G** to grab/move
3. Watch as all tangents and curves update in real-time!
4. Press ESC to cancel or click to confirm

---

## 🏗️ Architecture

```
Saikei Civil_ext/
├── blender_manifest.toml    # Extension metadata
├── __init__.py               # Main registration
├── core/                     # Core systems
│   ├── native_ifc_manager.py         # IFC file lifecycle, spatial hierarchy
│   ├── native_ifc_alignment.py       # Alignment data model (PI-based)
│   ├── alignment_visualizer.py       # Blender visualization
│   ├── alignment_registry.py         # Instance management
│   ├── complete_update_system.py     # Real-time update handler
│   ├── ifc_relationship_manager.py   # IFC relationship utilities
│   └── ...
├── operators/                # Interactive tools
│   ├── pi_operators.py               # PI placement (interactive + manual)
│   ├── curve_operators.py            # Curve insertion tool
│   ├── alignment_operators.py        # Alignment creation/management
│   ├── ifc_hierarchy_operators.py    # IFC file operations
│   └── ...
└── ui/                       # User interface
    ├── alignment_panel.py            # Main alignment UI
    ├── file_management_panel.py      # IFC file management UI
    ├── alignment_properties.py       # Property definitions
    └── panels/                       # Additional panels
        ├── georeferencing_panel.py
        ├── vertical_alignment_panel.py
        └── cross_section_panel.py
```

---

## 🔧 Development

### Reload Extension After Changes

**Option 1: Disable/Re-enable**
1. Edit > Preferences > Get Extensions
2. Disable Saikei Civil
3. Re-enable Saikei Civil

**Option 2: Refresh Extensions**
1. Edit > Preferences > Get Extensions
2. Click the refresh icon ⟳

### Console Output

Saikei Civil provides detailed console logging:
- `[Alignment]` - Alignment operations (PI updates, segment regeneration)
- `[Visualizer]` - Visualization updates
- `[Saikei Civil]` - Update system events
- `[CurveTool]` - Curve insertion operations

Open Blender's System Console: `Window > Toggle System Console`

---

## 📋 Requirements

- **Blender 4.5+** (uses modern extension system)
- **ifcopenshell** (bundled with Blender 4.5+)
- **BlenderBIM** (optional, but fully compatible)

---

## 🎯 Roadmap

- [ ] Spiral curve transitions (clothoids)
- [ ] Superelevation design
- [ ] 3D corridor modeling
- [ ] Earthwork quantities
- [ ] Profile view visualization
- [ ] Station/offset labeling
- [ ] Alignment reports and exports

---

## 🤝 Contributing

Saikei Civil is open-source and welcomes contributions! Whether it's bug reports, feature requests, or code contributions, we appreciate your help.

**Repository:** [https://github.com/DesertSpringsCivil/Saikei Civil](https://github.com/DesertSpringsCivil/Saikei Civil)

---

## 📜 License

See LICENSE file for details.

---

## 🙏 Credits

Built with:
- **Blender** - 3D creation suite
- **ifcopenshell** - IFC file processing
- **BlenderBIM** - IFC integration for Blender

Generated with assistance from **Claude Code** (Anthropic)

---

## 📝 Version History

### Current (Main Branch)
- ✅ Real-time PI updates with depsgraph handler
- ✅ Integrated curve insertion with automatic geometry updates
- ✅ BlenderBIM compatibility (no modal operator conflicts)
- ✅ IFC spatial hierarchy visualization
- ✅ File management (New/Open/Save IFC)
- ✅ Georeferencing panel
- ✅ Cross section tools
- ✅ Vertical alignment support

### v0.5.0 (Previous)
- Initial extension system migration
- Basic alignment creation

---

## 📄 License

**Copyright © 2025 Michael Yoder / Desert Springs Civil Engineering PLLC**

Saikei Civil is licensed under the **GNU General Public License v3 (GPL-3.0)**.

This means you can:
- ✅ Use it commercially
- ✅ Modify and distribute it
- ✅ Use it privately
- ✅ Study how the program works

**Requirements:**
- Include the original copyright notice and license
- State any significant changes made
- Distribute modified versions under GPL v3
- Make source code available when distributing

See the [LICENSE](LICENSE) file for full terms.

For commercial licensing inquiries or custom development, contact:
**Desert Springs Civil Engineering PLLC**

---

**Made with ❤️ for the civil engineering community**
