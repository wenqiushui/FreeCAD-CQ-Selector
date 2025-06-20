# FreeCAD CQ-Selector (中文版)

**为 FreeCAD 带来 CadQuery 强大的选择器语法，且无需任何外部依赖。**

![选择器演示](https://i.imgur.com/your-image-url.gif)  <!-- 建议：创建一个简短的GIF来展示其功能，并替换此链接 -->

## 项目简介

**FreeCAD CQ-Selector** 是一个独立的Python模块，旨在解决FreeCAD脚本编程中的一个常见痛点：如何方便地选择几何特征（面、边、顶点），尤其是在**无头模式 (Headless Mode)** 下。

您不再需要编写复杂的循环逻辑或依赖图形界面，只需使用由 [CadQuery](https://github.com/CadQuery/cadquery) 推广的、强大且直观的选择器语法即可。例如，您可以用一个简单的字符串 `">Z"` 来选中一个零件最顶部的那个面。

本插件的特点：
*   **完全独立**: **不**需要安装CadQuery库。它直接复刻了CadQuery的选择器算法。
*   **轻量级**: 仅有一个依赖库 `pyparsing`，这是一个用于构建语法解析器的标准工具。
*   **功能强大**: 支持复杂、链式和逻辑组合的选择，例如 `">Z and |X"` 或 `not <Y`。
*   **为无头模式而生**: 从设计之初就致力于为您的自动化脚本赋能。

## 安装指南

### 步骤一：安装 `pyparsing` 依赖库

本插件需要 `pyparsing` 库。您必须将其安装到FreeCAD自带的Python环境中。

*   **找到您FreeCAD环境中的 `pip`**:
    *   **Windows**: `C:\path-to-your-freecad\bin\pip.exe`
    *   **macOS**: `/Applications/FreeCAD.app/Contents/Resources/bin/pip`
    *   **Linux (AppImage)**: 首先，解压AppImage (`./your-freecad.AppImage --appimage-extract`)，然后在 `squashfs-root/usr/bin/` 目录下找到 `pip`。
    *   **Linux (通过包管理器安装)**: 如果FreeCAD使用系统Python，则可能是系统的 `pip`；否则，它通常位于安装路径下，如 `/usr/lib/freecad/bin/pip`。

*   **在终端或命令提示符中运行安装命令**:
    ```bash
    # (请将此路径替换为您真实的pip路径)
    /path/to/your/freecad/bin/pip install pyparsing
    ```

### 步骤二：安装插件

您有两种方式安装CQ-Selector插件：

#### 方式A：通过FreeCAD插件管理器 (推荐)

*(一旦该插件被收录进官方的FreeCAD-addons仓库，即可使用此方法)*

1.  打开FreeCAD。
2.  导航至 **工具 → 插件管理器**。
3.  在列表中找到 `CQ-Selector` 并点击“安装”。
4.  重启FreeCAD。

#### 方式B：手动安装

1.  下载本仓库的源代码，例如点击 **Code → Download ZIP**。
2.  找到您的FreeCAD的`Mod`（模块）目录。您可以在FreeCAD的Python控制台中输入 `FreeCAD.getUserAppDataDir() + "Mod"` 来找到它。
    *   **Windows**: `%APPDATA%\FreeCAD\Mod\`
    *   **macOS**: `~/Library/Application Support/FreeCAD/Mod/`
    *   **Linux**: `~/.local/share/FreeCAD/Mod/` (或 `~/.FreeCAD/Mod/`)
3.  在 `Mod` 目录内，创建一个名为 `CQ-Selector` 的新文件夹。
4.  将本仓库中的 `cq_selector.py` 文件复制到刚刚创建的 `CQ-Selector` 文件夹中。

您最终的目录结构应如下所示：
```
<你的FreeCAD-Mod目录>/
└── CQ-Selector/
    └── cq_selector.py
```

## 在无头模式下使用

在您的脚本中使用本选择器非常简单。主要入口点是 `StringSyntaxSelector` 类。

以下是一个完整的示例，展示了如何在无GUI环境下创建一个零件、选择其顶部边缘并应用圆角。

**脚本文件: `create_fillet_headless.py`**
```python
import sys
import FreeCAD
import Part
from FreeCAD import Base

# --- 环境设置: 添加FreeCAD库的路径 ---
# (请根据您的FreeCAD安装路径调整)
# Linux 示例:
sys.path.append('/usr/lib/freecad/lib')
# Windows 示例:
# sys.path.append('C:/Program Files/FreeCAD 0.21/bin')

# --- 主脚本 ---
try:
    # 1. 从插件中导入选择器类
    from cq_selector import StringSyntaxSelector
    print("成功导入 StringSyntaxSelector。")

    # 2. 创建一个基础形状
    box = Part.makeBox(30, 40, 50)
    print("基础长方体已创建。")

    # 3. 获取需要被筛选的边列表
    #    一个好的实践是：只获取一次列表并将其存入变量。
    all_edges = box.Edges

    # 4. 根据您的查询条件，创建一个选择器实例
    #    查询条件: 选择Z轴坐标最高的边
    selector = StringSyntaxSelector(">Z")
    print(f"选择器已创建，查询语句为: '{selector.selectorString}'")

    # 5. 应用选择器进行筛选
    top_edges = selector.filter(all_edges)
    print(f"选择器找到了 {len(top_edges)} 条顶部的边。")
    
    if not top_edges:
        raise RuntimeError("选择器未能找到任何边，程序中止。")

    # 6. 将选中的对象列表传入FreeCAD的API中
    #    'makeFillet' 函数期望接收一个包含边对象的列表。
    radius = 2.5
    filleted_box = box.makeFillet(radius, top_edges)
    print(f"半径为 {radius} 的圆角已成功应用。")

    # 7. 保存结果
    output_file = "filleted_part_cn.step"
    filleted_box.exportStep(output_file)
    print(f"结果已保存至 '{output_file}'")


except ImportError:
    print("错误: 无法导入 'cq_selector'。")
    print("请确认CQ-Selector插件已正确安装在您的Mod目录下。")
except Exception as e:
    print(f"程序发生错误: {e}")

```

### 如何运行脚本

将以上代码保存为 `create_fillet_headless.py`，打开您的终端（命令提示符），然后使用FreeCAD的命令行工具来执行它：

```bash
# 在 Linux/macOS 上
freecadcmd create_fillet_headless.py

# 在 Windows 上
FreeCADCmd.exe create_fillet_headless.py
```
脚本运行后，您会在同一目录下发现一个名为 `filleted_part_cn.step` 的新文件。您可以在FreeCAD或任何其他CAD软件中打开它来查看结果。

## 支持的选择器语法

本插件支持非常丰富的选择器语法，包括：

| 语法          | 含义                                        |
|---------------|---------------------------------------------|
| `>Z`, `<X`    | 沿坐标轴最远/最近的物体中心。               |
| `|Y`, `|X`    | 与坐标轴平行的边/面。                       |
| `+Z`, `-X`    | 法线方向与坐标轴正/负方向一致的面或边。     |
| `#Z`, `#XY`   | 与坐标轴垂直的面或边。                      |
| `%PLANE`      | 特定几何类型的物体 (PLANE, LINE, CIRCLE 等)。|
| `>Z[-2]`      | 倒数第二个物体。                            |
| `>X and <Y`  | 逻辑“与”操作。                              |
| `|X or |Y`   | 逻辑“或”操作。                              |
| `not >Z`      | 逻辑“非”操作。                              |

以及更多复杂的组合。由于本插件的语法是CadQuery的直接对应实现，您可以参考 [CadQuery选择器官方文档](https://cadquery.readthedocs.io/en/latest/selectors.html) 以获取更深入的信息。

## 贡献代码

欢迎任何形式的贡献！如果您发现了Bug、有功能建议，或者希望改进代码，请随时提交一个Issue或Pull Request。

## 许可协议

本项目基于 [MIT License](LICENSE) 开源。
