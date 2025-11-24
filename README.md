# NozzleCalc 🚀

**Optimized Rocket Nozzle Geometry Calculator**

NozzleCalc is a specialized application designed to calculate optimized geometries for rocket motor/engines (Rao Approximation/Bell Nozzle) through simple inputs based on project conception and internal ballistics data.

Developed by the **Kosmos Rocketry** Propulsion Sector.

---

## 📥 Download

No installation is required. Download the latest portable version for Windows:

[**⬇️ DOWNLOAD NozzleCalc.exe (Latest Version)**](https://github.com/joseroberto1540/NozzleCalc/releases/)

*The application features an **Auto-Update** system. It will automatically check for new versions upon launch.*

---

## ✨ Key Features

* **Rao Approximation (Bell Nozzle):** Accurate calculation of nozzle contours using the method of characteristics approximation.
* **Real-Time Visualization:** Interactive 2D plotting of the nozzle profile with "snapping" cursor for precise coordinate reading (N, Q, E points).
* **Project Management:** Save and Open your engine configurations (`.json` files) to manage multiple projects easily.
* **Multilingual Interface:** Full support for English and Portuguese (PT-BR).
* **Embedded Documentation:** Integrated Theory Manual PDF accessible directly within the app.
* **User-Friendly UI:** Modern Dark Mode interface built with CustomTkinter.

---

## 🛠️ Usage Instructions

1.  **Download:** Click the link above to download the executable file.
2.  **Run:** Double-click `NozzleCalc.exe`. Windows might ask for permission since it's a new engineering tool; allow it to run.
3.  **Input Data:** Enter your motor/engine parameters in the sidebar (Throat Radius, Chamber Pressure, Exhaust Pressure, etc.).
4.  **Compute:** Press `ENTER` or click "COMPUTE GEOMETRY".
5.  **Analyze:**
    * Use the **2D Visualization** tab to inspect the geometry. Hover over the graph to see coordinates.
    * Use the **Technical Data** tab for precise numerical outputs (Lengths, Expansion Ratios, Angles).
6.  **Save:** Use the toolbar at the top to Save (`Ctrl+S` equivalent) your project for later use.

---

## 📜 License & Attribution

This software was created and developed by the **Propulsion Sector of Kosmos Rocketry**.

**Attribution Required:**
Any use of this software, whether for academic, personal, or commercial projects, **must clearly credit Kosmos Rocketry**.

---

## 📦 Updates

### v3.2.2 - What's New:
* **🚀 Propellant Presets:** Added a dropdown menu with common solid propellants (KNSB, KNDX, APCP, etc.). Selecting a preset automatically fills and locks the Specific Heat Ratio ($k$) field to prevent errors.
* **🔍 Advanced Visualization:**
    * **Zoom & Pan:** Interactive graph with scroll-to-zoom and click-to-drag panning.
    * **Reset View:** Added a button to instantly restore the original view.
    * **Conical Reference:** Toggleable comparison with a conical nozzle based on the user's divergent angle.
* **⚙️ Physics & Geometry:**
    * **Throat Rounding Factor:** New input to adjust the curvature radius at the throat section.
    * **Convergence Check:** Enhanced logic to detect invalid geometries (inverted curvature) with a visual Status Indicator (Green/Red).
* **🎨 UI Improvements:** New Top Toolbar for file management and sidebar dedicated to inputs.
* **🐛 Bug Fixes:** Fixed Windows Taskbar icon persistence and JSON project loading issues.
