# Saikei Civil - IFC-Native Civil Engineering for Blender

**A modern Blender extension for civil engineering design using IFC 4.3 (IFC4X3_ADD2) standards.**

Saikei Civil brings professional-grade civil engineering tools directly into Blender, leveraging the power of IFC (Industry Foundation Classes) for data-driven infrastructure design. While [Bonsai](https://bonsaibim.org/) crafts the buildings, Saikei shapes the world around them.

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
- Compatible with Bonsai's transform tools

### 📐 Vertical Alignment Design

- PVI-based (Point of Vertical Intersection) design workflow
- Grade and vertical curve definitions
- Profile view visualization overlay
- IFC-native vertical alignment entities

### 🛤️ Corridor Generation

- Native IFC corridor creation using `IfcSectionedSolidHorizontal`
- Cross-section profiles stored as `IfcArbitraryOpenProfileDef`
- Component-based cross-section assembly system
- Full integration with IFC spatial hierarchy

### 🏗️ IFC Spatial Hierarchy

**Full IFC 4.3 Compliance**
- Proper spatial structure: `IfcProject → IfcSite → IfcRoad → IfcAlignment`
- All geometric elements are native IFC entities (`IfcAlignmentSegment`, etc.)
- Organizational empties for Alignments and Geomodels
- Blender Outliner hierarchy mirrors IFC structure via parenting
- Approximately 95% compliant with buildingSMART validation

**Bonsai Integration**
- Fully compatible with the Bonsai (formerly BlenderBIM) extension
- No conflicts with Bonsai's modal operators or transform systems
- Works alongside Bonsai for complete BIM workflows
- IFC entities properly linked and managed

### 🗺️ Georeferencing

- CRS (Coordinate Reference System) search and selection
- Project georeferencing with Map Conversion support
- IFC-native georeferencing entities (`IfcMapConversion`, `IfcProjectedCRS`)
- Defers to Bonsai's georeferencing when available

### 📐 Cross Sections

- Interactive cross-section editor with overlay visualization
- Component-based assembly system
- Import/export capabilities
- Template-based workflows

### 🔄 Transaction System

- Undo/redo infrastructure for IFC operations
- `IfcRebuilderRegistry` for IFC-as-source-of-truth workflows
- Parametric constraints for maintaining element relationships

### 📁 File Management

- Create new IFC files with proper hierarchy
- Open existing IFC files
- Save IFC to disk
- File information display (entity counts, schema version)

---

## 🚀 Installation

### Method 1: Symlink (Recommended for Development)

Run this command in **Command Prompt (Administrator)**:

```cmd
mklink /D "C:\Users\[YourUsername]\AppData\Roaming\Blender Foundation\Blender\4.5\extensions\user_default\saikei_civil" "C:\Path\To\SaikeiCivil\saikei_civil"
```

Replace `[YourUsername]` and `C:\Path\To\SaikeiCivil` with your actual paths.

### Method 2: Direct Copy

Copy the entire `saikei_civil` folder to:
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

Saikei Civil uses a **three-layer architecture** that separates pure Python logic from Blender-specific code:

```
saikei_civil/
├── blender_manifest.toml     # Extension metadata
├── __init__.py               # Main registration
│
├── core/                     # Layer 1: Pure Python (NO bpy imports)
│   ├── ifc_manager/          # IFC file lifecycle
│   │   ├── manager.py        # NativeIfcManager
│   │   ├── transaction.py    # TransactionManager
│   │   └── rebuilder_registry.py  # IFC-as-source-of-truth undo/redo
│   ├── horizontal_alignment/ # PI-based alignment design
│   ├── vertical_alignment/   # PVI-based vertical design
│   └── components/           # Cross-section assembly system
│
├── tool/                     # Layer 2: Blender implementations
│   ├── ifc.py                # Unified IFC access (Bonsai bridge)
│   ├── blender.py            # Blender utilities
│   ├── alignment.py          # Alignment tools
│   └── georeference.py       # Georeferencing tools
│
├── operators/                # Layer 3: Blender operators
│   ├── pi_operators.py       # PI placement (interactive + manual)
│   ├── curve_operators.py    # Curve insertion tool
│   ├── alignment_operators.py
│   ├── corridor_operators.py
│   └── ...
│
├── ui/                       # Layer 3: User interface
│   ├── alignment_panel.py
│   ├── file_management_panel.py
│   └── panels/
│       ├── georeferencing_panel.py
│       ├── vertical_alignment_panel.py
│       ├── cross_section_panel.py
│       └── corridor_panel.py
│
└── handlers/                 # Blender event handlers
    └── depsgraph_handler.py  # Real-time update system
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

- **Blender 4.5 - 5.1** (uses modern extension system)
- **ifcopenshell** (bundled with Blender 4.5+)
- **Bonsai** (optional, but fully compatible)

---

## 🎯 Roadmap

- [x] ~~3D corridor modeling~~ ✅ v0.7.0
- [x] ~~Profile view visualization~~ ✅ v0.6.0
- [x] ~~Station markers~~ ✅ v0.6.0
- [ ] Spiral curve transitions (clothoids)
- [ ] Superelevation design
- [ ] Earthwork quantities
- [ ] Alignment reports and exports
- [ ] IfcOpenShell alignment API integration

---

## 🤝 Contributing

Saikei Civil is open-source and welcomes contributions! Whether it's bug reports, feature requests, or code contributions, we appreciate your help.

**Repository:** [https://github.com/saikeicivil/SaikeiCivil](https://github.com/saikeicivil/SaikeiCivil)

---

## 🙏 Credits

Built with:
- **Blender** - 3D creation suite
- **ifcopenshell** - IFC file processing
- **Bonsai** - IFC integration for Blender

Generated with assistance from **Claude Code** (Anthropic)

---

## 📝 Version History

### v0.7.0 (January 2026)
- Native IFC corridor generation with `IfcSectionedSolidHorizontal`
- Three-layer architecture refactoring
- Transaction system with undo/redo infrastructure
- Parametric constraints system
- ~95% buildingSMART IFC 4.3 validation compliance
- License changed to GPL v3

### v0.6.0 (December 2025)
- Rebrand from BlenderCivil to Saikei Civil
- Profile view visualization overlay
- Visual station markers for alignments
- Cross-section overlay system

### v0.5.0
- Initial extension system migration
- Basic alignment creation

---

## 📄 License

**Copyright © 2025-2026 Michael Yoder / Desert Springs Civil Engineering PLLC**

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
