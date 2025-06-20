# FreeCAD CQ-Selector

**Brings the power of CadQuery's selector syntax to FreeCAD, with zero dependencies.**

![Selector Demo](https://i.imgur.com/your-image-url.gif)  <!-- 建议：创建一个简短的GIF来展示其功能，并替换此链接 -->

## Overview

**FreeCAD CQ-Selector** is a standalone Python module designed to solve a common challenge in FreeCAD: selecting geometric features (faces, edges, vertices) in scripts, especially in **headless mode**.

Instead of complex loops or relying on the GUI, this plugin allows you to use the intuitive and powerful selector syntax popularized by the [CadQuery](https://github.com/CadQuery/cadquery) project. For example, you can select the top-most face of a shape with a simple string: `">Z"`.

This plugin is:
*   **Standalone**: It does **not** require CadQuery to be installed. It is a direct adaptation of its selection algorithms.
*   **Lightweight**: It has only one dependency, the `pyparsing` library, which is a standard tool for creating parsers.
*   **Powerful**: Supports complex, chained, and logical selections like `">Z and |X"` or `not <Y`.
*   **Headless-Ready**: Designed from the ground up to empower your automation scripts.

## Installation

### 1. Install the `pyparsing` Dependency

This plugin requires the `pyparsing` library. You must install it into FreeCAD's internal Python environment.

*   **Find your FreeCAD `pip`**:
    *   **Windows**: `C:\path-to-your-freecad\bin\pip.exe`
    *   **macOS**: `/Applications/FreeCAD.app/Contents/Resources/bin/pip`
    *   **Linux (AppImage)**: First, extract the AppImage (`./your-freecad.AppImage --appimage-extract`), then find `pip` inside `squashfs-root/usr/bin/pip`.
    *   **Linux (Installed)**: It might be a system `pip` if FreeCAD uses the system Python, or a specific one like `/usr/lib/freecad/bin/pip`.

*   **Run the installation command** in your terminal/command prompt:
    ```bash
    # (Replace with the actual path to your pip)
    /path/to/your/freecad/bin/pip install pyparsing
    ```

### 2. Install the Plugin

There are two ways to install the CQ-Selector plugin:

#### Option A: Using the FreeCAD Addon Manager (Recommended)

*(This will be possible once the plugin is accepted into the official FreeCAD-addons repository)*

1.  Open FreeCAD.
2.  Go to **Tools → Addon Manager**.
3.  Find `CQ-Selector` in the list and click "Install".
4.  Restart FreeCAD.

#### Option B: Manual Installation

1.  Download this repository, for example by clicking **Code → Download ZIP**.
2.  Find your FreeCAD Mod directory. You can find this by opening FreeCAD and typing `FreeCAD.getUserAppDataDir() + "Mod"` in the Python Console.
    *   **Windows**: `%APPDATA%\FreeCAD\Mod\`
    *   **macOS**: `~/Library/Application Support/FreeCAD/Mod/`
    *   **Linux**: `~/.local/share/FreeCAD/Mod/` (or `~/.FreeCAD/Mod/`)
3.  Create a new folder inside the `Mod` directory named `CQ-Selector`.
4.  Copy the `cq_selector.py` file from this repository into the newly created `CQ-Selector` folder.

Your final directory structure should look like this:
```
<Your-FreeCAD-Mod-Directory>/
└── CQ-Selector/
    └── cq_selector.py```

## Usage in Headless Mode

Using the selector in your scripts is straightforward. The main entry point is the `StringSyntaxSelector` class.

Here is a complete example of creating a part, selecting its top edges, and applying a fillet, all without a GUI.

**`create_fillet_headless.py`**
```python
import sys
import FreeCAD
import Part
from FreeCAD import Base

# --- Setup: Add FreeCAD library path ---
# (Adjust this path to your FreeCAD installation)
# Example for Linux:
sys.path.append('/usr/lib/freecad/lib')
# Example for Windows:
# sys.path.append('C:/Program Files/FreeCAD 0.21/bin')

# --- Main Script ---
try:
    # 1. Import the selector class from the plugin
    from cq_selector import StringSyntaxSelector
    print("Successfully imported StringSyntaxSelector.")

    # 2. Create a base shape
    box = Part.makeBox(30, 40, 50)
    print("Base box created.")

    # 3. Get the list of edges to filter
    #    It's good practice to get the list once and store it.
    all_edges = box.Edges

    # 4. Create a selector instance with your desired query
    #    Query: Select edges that are highest along the Z-axis
    selector = StringSyntaxSelector(">Z")
    print(f"Selector created with query: '{selector.selectorString}'")

    # 5. Apply the filter
    top_edges = selector.filter(all_edges)
    print(f"Selector found {len(top_edges)} top edges.")
    
    if not top_edges:
        raise RuntimeError("Selector did not find any edges. Aborting.")

    # 6. Use the selected objects in a FreeCAD API
    #    The 'makeFillet' function expects a list of Edge objects.
    radius = 2.5
    filleted_box = box.makeFillet(radius, top_edges)
    print(f"Fillet of radius {radius} applied successfully.")

    # 7. Save the result
    output_file = "filleted_part.step"
    filleted_box.exportStep(output_file)
    print(f"Result saved to '{output_file}'")


except ImportError:
    print("Error: Could not import 'cq_selector'.")
    print("Please ensure the CQ-Selector plugin is installed correctly in your Mod directory.")
except Exception as e:
    print(f"An error occurred: {e}")

```

### How to Run the Script

Save the code above as `create_fillet_headless.py`, open your terminal, and run it using FreeCAD's command-line executable:

```bash
# On Linux/macOS
freecadcmd create_fillet_headless.py

# On Windows
FreeCADCmd.exe create_fillet_headless.py
```
After running, you will find a new file named `filleted_part.step` in the same directory, which you can open in FreeCAD or any other CAD program.

## Supported Selector Syntax

The plugin supports a wide range of selectors, including:

| Syntax          | Meaning                                            |
|-----------------|----------------------------------------------------|
| `>Z`, `<X`      | Furthest/nearest object center along an axis.      |
| `|Y`, `|X`      | Edges/Faces parallel to an axis.                   |
| `+Z`, `-X`      | Faces/Edges with normal pointing along an axis.    |
| `#Z`, `#XY`     | Faces/Edges perpendicular to an axis.              |
| `%PLANE`        | Objects of a specific geometric type (PLANE, LINE, CIRCLE, etc.). |
| `>Z[-2]`        | The second-to-last object.                         |
| `>X and <Y`    | Logical AND.                                       |
| `|X or |Y`     | Logical OR.                                        |
| `not >Z`        | Logical NOT.                                       |

...and many more combinations. For a deep dive, refer to the [CadQuery Selector documentation](https://cadquery.readthedocs.io/en/latest/selectors.html), as the syntax is designed to be a direct equivalent.

## Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to improve the code, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](LICENSE).
