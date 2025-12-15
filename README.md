# NozzleCalc Pro 🚀

**Advanced Bell Nozzle Design & Simulation Tool**


## 📖 Overview

**NozzleCalc Pro** is a specialized engineering software developed by the **Propulsion Sector of Kosmos Rocketry**. It is designed to calculate, optimize, and visualize the geometry of rocket engine nozzles using the **Rao Approximation (Bell Nozzle)** method.

Unlike simple conical nozzles, Bell nozzles offer higher efficiency by directing exhaust gases more parallel to the nozzle axis. This tool automates the complex method of characteristics required to design these contours, providing immediate visual feedback, physical validation, and manufacturing data.

---

## 📥 Installation & Download

### Portable Executable 
No Python installation is required. Just download, run, and design.

1.  Go to the **[Latest Release Page](https://github.com/joseroberto1540/NozzleCalc/releases)**.
2.  Download the `NozzleCalc.exe` file.
3.  Run the file. *(Windows might flag it as unrecognized software; this is normal for unsigned engineering tools. Click "Run Anyway").*

---

## ✨ Key Features

### 🧪 Propulsion Physics
* **Rao Approximation Algorithm:** Generates optimized contour data based on empirical parabolic approximation (parabola defined by throat entrance, throat exit, and nozzle exit angles).
* **Propellant Database:** Includes a built-in dropdown with specific heat ratio ($k$) presets for common propellants:
    * KNSB (Sorbitol)
    * KNDX / KNSu (Sugar)
    * APCP
    * Ethanol/LOX, Paraffin/N2O, and more.
* **Advanced Interpolation:** Supports any length percentage between 60% and 100% (automatically interpolates between Rao's 60%, 80%, and 90% datasets).

### 📐 Geometry & Validation
* **Convergence Checker:** Real-time validation engine that checks for physical impossibilities, such as inverted curvature or loop-backs. Displays a **GREEN (Converged)** or **RED (Diverged)** status instantly.
* **Throat Rounding Factor:** Fine-tune the curvature radius at the throat ($R_{div}$) to adjust for manufacturing constraints or thermal considerations.
* **Conical Comparison:** Toggle a 15° (or custom angle) conical nozzle reference overlay to visualize length and mass savings.
* **Efficiente Calculation:** A well-designed Bell nozzle readily achieves an efficiency factor of at least 96.5%, even while being shorter than an equivalent conical nozzle. The system allows users to generate the nozzle profile and evaluate its efficiency in real-time.

### 🖥️ Interactive Visualization
* **Dynamic Plotting:** High-resolution rendering using Matplotlib embedded in a modern UI.
* **Zoom & Pan:** Inspect the throat region or exit section in detail using scroll-to-zoom and click-to-drag panning.
* **Snapping Cursor:** Mouse over key points (N, Q, E) to reveal precise X/Y coordinates in millimeters.

### 💾 Workflow & Usability
* **Project Management:** Save your engine configurations as `.json` files and reload them later.
* **Auto-Update:** The application automatically checks GitHub Releases for updates upon launch.
* **Modern UI:** Built with CustomTkinter for a sleek, Dark Mode interface.
* **Integrated Documentation:** A complete Theory Manual (PDF) is embedded within the application.

---

## 🛠️ User Guide

1.  **Propellant Selection:** Choose a preset from the dropdown (e.g., "KNSB"). The Specific Heat Ratio ($k$) field will be automatically filled and locked. Select "Custom" to enter a manual value.
2.  **Input Parameters:**
    * **Throat Radius ($R_t$):** The radius of the narrowest point.
    * **Pressure:** Chamber ($P_c$) and Exit ($P_e$) pressures.
    * **Angles:** Set the Divergent and Convergent angles.
    * **Length %:** Define how short the nozzle is compared to a 15° cone (standard Rao bell is 80%).
3.  **Compute:** Press `ENTER` or click the **COMPUTE GEOMETRY** button.
4.  **Analyze:**
    * Check the **Status Box** above the graph.
    * Use the **Technical Data** tab to read exact lengths, expansion ratios ($\epsilon$), and areas.
    * Hover over the graph to see exact coordinates for CAD export.
5.  **Compare:** Check the "Show Conical Ref." box to see the difference in length.
6.  **Save:** Use the "Save" button in the top toolbar to keep your project.

---

## 📚 Theory Reference

This tool implements the **Rao Method of Characteristics Approximation**.

The contour is constructed using a parabola defined by:
* **Region 1 (Convergent):** Circular arc.
* **Region 2 (Throat):** Circular arc defined by $R_{div}$.
* **Region 3 (Divergent Bell):** A quadratic Bézier curve (parabola) defined by three points:
    * **N (Inflection):** Where the throat curve ends.
    * **E (Exit):** The final radius and length coordinates.
    * **Q (Control):** Intersection of the slope at N and the slope at E.

For a deep dive into the equations, click the **"📘 Theory Manual"** button inside the application.

---

## 📜 License & Attribution

**© Kosmos Rocketry - Propulsion Sector**

This software is provided "as is" for educational and engineering development purposes.

* **Attribution:** Any use of this software, screenshots, or data derived from it in academic papers, commercial projects, or public displays must explicitly credit **Kosmos Rocketry**.
* **Liability:** The developers are not responsible for hardware failures resulting from the use of these geometries. Always verify designs with CFD analysis before manufacturing.

---
*[Report a Bug](https://github.com/joseroberto1540/NozzleCalc/issues) | [Visit Kosmos Rocketry](https://instagram.com/kosmosrocketry)*