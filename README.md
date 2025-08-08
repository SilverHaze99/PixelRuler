# PixelRuler - OSINT Image Measurement Tool

**PixelRuler** is a specialized computer vision tool designed for Open Source Intelligence (OSINT) analysts to perform precise measurements on digital images. The tool enables analysts to measure objects in images using known reference objects or collect pixel-based measurements for later scaling.

## Purpose

PixelRuler solves a common OSINT challenge: determining the real-world size of objects in images. By using reference objects of known dimensions, analysts can:

- Measure unknown objects using known references (phones, credit cards, coins, etc.)
- Build measurement chains across multiple images
- Document findings with precise measurements and timestamps
- Export data for further analysis

## Key Features

- **Interactive Measurement**: Point-and-click interface for drawing measurement lines
- **Reference Object Database**: Pre-loaded common objects with real-world dimensions
- **Optional Scaling**: Save pixel-only measurements when no reference is available
- **Zoom & Pan**: Detailed examination of high-resolution images (up to 10x zoom)
- **Data Persistence**: Automatic saving/loading of measurements per image
- **Export Capabilities**: CSV export for integration with analysis workflows
- **Chain of Custody**: Timestamped measurements for documentation

## Installation

### Requirements
- Python 3.7+
- OpenCV (cv2)
- NumPy
- Tkinter (usually included with Python)

### Setup

1.  **Clone the repository** (if you are using Git):
    ```bash
    git clone https://github.com/SilverHaze99/PixelRuler
    cd PixelRuler
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```
3.  **Activate the virtual environment:**
    * **On Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    * **On macOS and Linux:**
        ```bash
        source venv/bin/activate
        ```
4.  **Install Required Python Libraries:** Install the necessary libraries using pip within the activated virtual environment:
```bash
pip install opencv-python numpy
```
5.  **Run the tool**
```bash   
python pixelruler.py
```

## Usage

### Basic Controls
- **'l'**: Load image
- **Left Click**: Set measurement points (2 points = 1 measurement)
- **Ctrl + Mouse Wheel**: Zoom in/out around cursor
- **Ctrl + Left Click + Drag**: Pan image
- **'t'**: Toggle measurement visibility
- **'d'**: Delete last measurement
- **'m'**: Show measurement list in console
- **'s'**: Save annotated image
- **'e'**: Export measurements to CSV
- **'r'**: Reset view (zoom & position)
- **'q'**: Quit application

### Measurement Workflow

1. **Load Image** - Press 'l' and select your image file
2. **Set Points** - Click two points to create a measurement line
3. **Save Decision** - Choose whether to save this measurement
4. **Reference Object** - Optionally select a reference object for real-world scaling
5. **Repeat** - Continue measuring other objects

### Reference Objects Database

PixelRuler includes common OSINT reference objects:

| Object | Dimensions | Notes |
|--------|-----------|--------|
| iPhone 14 | 147.5 × 71.5 mm | Latest model dimensions |
| iPhone 15 | 147.6 × 71.6 mm | Current flagship |
| Samsung Galaxy S24 | 147.0 × 70.6 mm | Android reference |
| Credit Card | 85.60 × 53.98 mm | ISO/IEC 7810 standard |
| Cigarette Pack | 87.0 × 55.0 mm | Standard pack size |
| Euro Coin (1€) | ⌀23.25 mm | Common European reference |
| US Quarter | ⌀24.26 mm | US currency reference |
| Standard Pen | 140.0 mm | Typical ballpoint pen |
| Custom | User-defined | Enter your own measurements |

## Data Management

### File Structure
```
your_image.jpg                    # Original image
your_image_measurements.json      # Measurement data
your_image_annotated.png         # Annotated image (optional)
your_image_measurements.csv      # Exported data (optional)
```

### JSON Data Format
```json
{
  "image_path": "path/to/image.jpg",
  "image_size": {"width": 1920, "height": 1080},
  "created": "2024-01-15T14:30:00",
  "measurements": [
    {
      "id": 1,
      "start": {"x": 100.5, "y": 200.3},
      "end": {"x": 250.7, "y": 200.3},
      "pixel_length": 150.2,
      "timestamp": "2024-01-15T14:31:22",
      "reference_object": {
        "name": "iPhone 14",
        "length": 147.5,
        "unit": "mm"
      },
      "real_world_length": 147.5,
      "scale_factor": 0.982
    }
  ]
}
```

## 🔗 OSINT Measurement Chains

PixelRuler enables analysts to build measurement chains across multiple images:

### Scenario Example:
1. **Image 1**: Contains iPhone (known) + Unknown Object X
   - Measure iPhone: 150px = 147.5mm
   - Measure Object X: 200px = 196.7mm
   - Scale factor: 0.983 mm/px

2. **Image 2**: Contains Object X (now known) + Unknown Object Y  
   - Enter Object X as custom reference: 196.7mm
   - Measure Object Y using Object X as reference

3. **Image 3**: Use Object Y as new reference for Object Z

## Visual Features

- **Color-coded measurements**: Each measurement gets a unique color
- **Numbered annotations**: Clear identification of measurements
- **Dual-unit display**: Shows both pixel and real-world values
- **Zoom-adaptive text**: Labels scale with zoom level
- **Non-destructive editing**: Original image remains unchanged

## Export & Analysis

### CSV Export Fields:
- **ID**: Measurement identifier
- **Pixel_Length**: Length in pixels
- **Real_Length**: Calculated real-world length
- **Unit**: Measurement unit (mm, etc.)
- **Reference_Object**: Used reference object name
- **Scale_Factor**: Pixels-to-real-world ratio
- **Start_X/Y, End_X/Y**: Precise coordinates
- **Timestamp**: When measurement was created

### Integration Tips:
- Import CSV into Excel/Google Sheets for calculations
- Use measurement data in GIS software
- Combine with metadata extraction tools
- Build measurement databases for recurring objects

## Advanced Features

### Measurement Management
- **Persistent storage**: Measurements auto-save and reload
- **Selective saving**: Choose which measurements to keep
- **Flexible referencing**: Mix pixel-only and scaled measurements
- **Error recovery**: Delete incorrect measurements easily

### Technical Capabilities
- **High precision**: Sub-pixel accuracy for measurements
- **Large image support**: Handle high-resolution images efficiently
- **Memory efficient**: Optimized display rendering
- **Cross-platform**: Works on Windows, Mac, Linux

## OSINT Use Cases

### Social Media Analysis
- Verify claimed locations using architectural elements
- Estimate crowd sizes using known objects for scale
- Analyze weapon sizes in conflict imagery

### Geospatial Intelligence
- Measure vehicle dimensions from satellite imagery
- Calculate building heights using shadow measurements
- Assess infrastructure dimensions for capacity analysis

### Digital Forensics
- Verify image authenticity through measurement consistency
- Analyze evidence photos with reference objects
- Document crime scenes with precise measurements

### Research & Journalism
- Fact-check claims about object sizes
- Analyze industrial facilities and equipment
- Investigate environmental changes over time

## Best Practices

### Measurement Accuracy
- Choose reference objects visible in the same plane as target
- Account for perspective distortion in angled shots
- Use multiple reference objects when available
- Document uncertainty in measurements

### Documentation
- Always timestamp measurements for chain of custody
- Export data regularly for backup
- Use descriptive filenames for easy identification
- Keep original images unchanged

### Quality Control
- Cross-reference measurements when possible
- Verify reference object dimensions from reliable sources
- Consider lighting and shadow effects on apparent size
- Document assumptions and limitations

## Contributing

PixelRuler is designed to be easily extensible:

### Adding Reference Objects
Edit the `REFERENCE_OBJECTS` dictionary in the source code:
```python
"New Object": {"length": 100.0, "width": 50.0, "unit": "mm"}
```

### Feature Requests
- Angle measurements
- Area calculations  
- Batch processing capabilities
- Integration with mapping software

## License

This tool is provided as-is for OSINT research and analysis purposes. Users are responsible for ensuring compliance with applicable laws and regulations in their jurisdiction.
This tool is provided under the MIT-License

## Technical Details

### System Requirements
- **RAM**: 4GB minimum, 8GB recommended for large images
- **Storage**: 100MB for application, additional space for measurement data
- **Display**: 1920×1080 minimum resolution recommended

### Supported Formats
- **Input**: JPEG, PNG, BMP, TIFF
- **Output**: PNG (annotated images), JSON (measurements), CSV (data export)

### Performance Notes
- Images over 4K resolution may require more RAM
- Zoom operations are optimized for smooth performance
- Measurement data files are typically <1MB per image

---

**PixelRuler** - Precision measurement for the digital investigator.

*Version 1.0*
