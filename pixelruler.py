import cv2
import numpy as np
import json
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os
from datetime import datetime

# Global variables
image = None
original_image = None
image_display = None
points = []
measurements = []
show_measurements = True
window_name = "PixelRuler"
zoom_factor = 1.0
min_zoom = 0.1
max_zoom = 10.0
offset_x = 0
offset_y = 0
panning = False
last_mouse_x = 0
last_mouse_y = 0
current_mouse_x = 0
current_mouse_y = 0
current_image_path = ""

# Performance optimization variables
last_update_time = 0
update_interval = 16  # ~60 FPS limit (16ms)
needs_redraw = True
cached_scaled_image = None
cached_zoom = 0
cached_image_hash = 0

# Reference object database (expandable)
REFERENCE_OBJECTS = {
    "iPhone 14": {"length": 147.5, "width": 71.5, "unit": "mm"},
    "iPhone 15": {"length": 147.6, "width": 71.6, "unit": "mm"},
    "Samsung Galaxy S24": {"length": 147.0, "width": 70.6, "unit": "mm"},
    "Credit Card": {"length": 85.60, "width": 53.98, "unit": "mm"},
    "Cigarette Pack": {"length": 87.0, "width": 55.0, "unit": "mm"},
    "Euro Coin (1€)": {"diameter": 23.25, "unit": "mm"},
    "US Quarter": {"diameter": 24.26, "unit": "mm"},
    "Standard Pen": {"length": 140.0, "unit": "mm"},
    "Custom": {"length": 0, "width": 0, "unit": "mm"}
}

def load_image():
    """Load an image and initialize display."""
    global image, original_image, image_display, zoom_factor, offset_x, offset_y, current_image_path, points, measurements
    global cached_scaled_image, cached_zoom, cached_image_hash, needs_redraw
    
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select image for analysis",
        filetypes=[("All Images", "*.jpg *.jpeg *.png *.bmp *.tiff"), 
                   ("JPEG", "*.jpg *.jpeg"), 
                   ("PNG", "*.png")]
    )
    if file_path:
        original_image = cv2.imread(file_path)
        if original_image is None:
            messagebox.showerror("Error", "Failed to load image.")
            return
        
        image = original_image.copy()
        image_display = image.copy()
        current_image_path = file_path
        zoom_factor = 1.0
        offset_x = 0
        offset_y = 0
        points = []
        measurements = []
        
        # Reset cache
        cached_scaled_image = None
        cached_zoom = 0
        cached_image_hash = hash(image.tobytes())
        needs_redraw = True
        
        # Load existing measurements if available
        load_measurements()
        update_display()
        print(f"Image loaded: {os.path.basename(file_path)}")
        print(f"Image size: {image.shape[1]}x{image.shape[0]} pixels")

def to_image_coords(x_screen, y_screen):
    """Convert screen coordinates to image coordinates."""
    global zoom_factor, offset_x, offset_y, image
    if image is None:
        return 0, 0
    x_img = (x_screen - offset_x) / zoom_factor
    y_img = (y_screen - offset_y) / zoom_factor
    x_img = max(0, min(x_img, image.shape[1]))
    y_img = max(0, min(y_img, image.shape[0]))
    return x_img, y_img

def to_screen_coords(x_img, y_img):
    """Convert image coordinates to screen coordinates."""
    global zoom_factor, offset_x, offset_y
    x_screen = x_img * zoom_factor + offset_x
    y_screen = y_img * zoom_factor + offset_y
    return x_screen, y_screen

def ask_save_measurement():
    """Ask user if they want to save the measurement."""
    root = tk.Tk()
    root.withdraw()
    result = messagebox.askyesno("Save Measurement", "Do you want to save this measurement?")
    return result

def select_reference_object():
    """Dialog for selecting a reference object (optional)."""
    root = tk.Tk()
    root.withdraw()
    
    # Ask if user wants to add reference object
    add_ref = messagebox.askyesno("Reference Object", "Do you want to add a reference object for real-world scaling?")
    
    if not add_ref:
        return None
    
    # Create selection list
    objects = list(REFERENCE_OBJECTS.keys())
    
    choice = simpledialog.askstring(
        "Select Reference Object",
        f"Available objects:\n" + "\n".join([f"{i+1}: {obj}" for i, obj in enumerate(objects)]) + 
        f"\n\nEnter number (1-{len(objects)}):"
    )
    
    if choice and choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(objects):
            selected_obj = objects[idx]
            
            if selected_obj == "Custom":
                # Custom input
                name = simpledialog.askstring("Custom Object", "Object name:")
                length = simpledialog.askfloat("Custom Object", "Length (mm):")
                if name and length:
                    return {"name": name, "length": length, "unit": "mm"}
            else:
                obj_data = REFERENCE_OBJECTS[selected_obj].copy()
                obj_data["name"] = selected_obj
                return obj_data
    
    return None

def mouse_callback(event, x, y, flags, param):
    """Handle mouse events for points, panning and zooming."""
    global points, image_display, panning, last_mouse_x, last_mouse_y, offset_x, offset_y, zoom_factor, current_mouse_x, current_mouse_y
    global needs_redraw
    
    if image is None:
        return
        
    current_mouse_x, current_mouse_y = x, y
    
    if event == cv2.EVENT_LBUTTONDOWN and not (flags & cv2.EVENT_FLAG_CTRLKEY):
        # Set point in image coordinates
        img_x, img_y = to_image_coords(x, y)
        points.append((img_x, img_y))
        
        if len(points) % 2 == 0:
            # Two points -> create measurement
            start = points[-2]
            end = points[-1]
            pixel_length = np.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
            
            # Ask if user wants to save this measurement
            if not ask_save_measurement():
                # Remove the last two points if user doesn't want to save
                points.pop()
                points.pop()
                needs_redraw = True
                update_display()
                return
            
            # Ask for reference object (optional)
            ref_obj = select_reference_object()
            
            measurement = {
                "id": len(measurements) + 1,
                "start": {"x": float(start[0]), "y": float(start[1])},
                "end": {"x": float(end[0]), "y": float(end[1])},
                "pixel_length": float(pixel_length),
                "timestamp": datetime.now().isoformat(),
                "reference_object": ref_obj,
                "real_world_length": None,
                "scale_factor": None
            }
            
            # Calculate real length if reference object was selected
            if ref_obj:
                if "length" in ref_obj:
                    scale_factor = ref_obj["length"] / pixel_length
                elif "diameter" in ref_obj:
                    scale_factor = ref_obj["diameter"] / pixel_length
                else:
                    scale_factor = None
                
                if scale_factor:
                    measurement["scale_factor"] = float(scale_factor)
                    measurement["real_world_length"] = float(pixel_length * scale_factor)
            
            measurements.append(measurement)
            
            print(f"\nMeasurement #{measurement['id']} created:")
            print(f"  Pixels: {pixel_length:.2f} px")
            if measurement["real_world_length"]:
                print(f"  Real: {measurement['real_world_length']:.2f} {ref_obj.get('unit', 'mm')}")
                print(f"  Scale: 1 px = {measurement['scale_factor']:.4f} {ref_obj.get('unit', 'mm')}")
            if ref_obj:
                print(f"  Reference: {ref_obj['name']}")
            else:
                print(f"  Reference: None (pixel measurement only)")
            
            save_measurements()
        
        needs_redraw = True
        update_display()
    
    elif event == cv2.EVENT_LBUTTONDOWN and (flags & cv2.EVENT_FLAG_CTRLKEY):
        panning = True
        last_mouse_x = x
        last_mouse_y = y
    
    elif event == cv2.EVENT_MOUSEMOVE and panning and (flags & cv2.EVENT_FLAG_CTRLKEY):
        # Optimierung: Nur bei größeren Bewegungen neu zeichnen
        dx = x - last_mouse_x
        dy = y - last_mouse_y
        
        if abs(dx) > 2 or abs(dy) > 2:  # Mindestbewegung für Update
            last_mouse_x = x
            last_mouse_y = y
            offset_x += dx
            offset_y += dy
            needs_redraw = True
            update_display_throttled()
    
    elif event == cv2.EVENT_LBUTTONUP:
        panning = False
        if needs_redraw:
            update_display()
    
    elif event == cv2.EVENT_MOUSEWHEEL and (flags & cv2.EVENT_FLAG_CTRLKEY):
        old_zoom_factor = zoom_factor
        if flags > 0:
            zoom_factor *= 1.1
        else:
            zoom_factor /= 1.1
        zoom_factor = max(min_zoom, min(zoom_factor, max_zoom))
        
        factor = zoom_factor / old_zoom_factor
        offset_x = current_mouse_x - (current_mouse_x - offset_x) * factor
        offset_y = current_mouse_y - (current_mouse_y - offset_y) * factor
        needs_redraw = True
        update_display()

def update_display_throttled():
    """Throttled version of update_display for smooth panning."""
    global last_update_time
    import time
    current_time = time.time() * 1000  # Convert to milliseconds
    
    if current_time - last_update_time > update_interval:
        update_display()
        last_update_time = current_time

def get_cached_scaled_image():
    """Get cached scaled image or create new one if needed."""
    global cached_scaled_image, cached_zoom, image, zoom_factor
    
    if cached_scaled_image is None or abs(cached_zoom - zoom_factor) > 0.01:
        if image is None:
            return None
            
        # Scale the image
        scaled_width = int(image.shape[1] * zoom_factor)
        scaled_height = int(image.shape[0] * zoom_factor)
        
        if scaled_width <= 0 or scaled_height <= 0:
            return None
            
        # Choose interpolation based on zoom level for better performance/quality trade-off
        if zoom_factor < 1.0:
            interpolation = cv2.INTER_AREA  # Better for downsampling
        else:
            interpolation = cv2.INTER_LINEAR  # Faster for upsampling
            
        cached_scaled_image = cv2.resize(image, (scaled_width, scaled_height), interpolation=interpolation)
        cached_zoom = zoom_factor
    
    return cached_scaled_image

def update_display():
    """Update image display with zoom, panning and measurements."""
    global image_display, needs_redraw
    if image is None or not needs_redraw:
        return
        
    disp_height, disp_width = image.shape[:2]
    image_display = np.zeros_like(image)
    
    scaled_image = get_cached_scaled_image()
    if scaled_image is None:
        cv2.imshow(window_name, image_display)
        return

    # Calculate visible area
    x_start = int(offset_x)
    y_start = int(offset_y)
    x_end = min(disp_width, x_start + scaled_image.shape[1])
    y_end = min(disp_height, y_start + scaled_image.shape[0])
    
    src_x_start = max(0, -x_start)
    src_y_start = max(0, -y_start)
    src_x_end = src_x_start + (x_end - max(0, x_start))
    src_y_end = src_y_start + (y_end - max(0, y_start))
    
    x_start = max(0, x_start)
    y_start = max(0, y_start)
    
    target_width = x_end - x_start
    target_height = y_end - y_start
    
    if target_width > 0 and target_height > 0 and src_x_end > src_x_start and src_y_end > src_y_start:
        source_region = scaled_image[src_y_start:src_y_end, src_x_start:src_x_end]
        if source_region.shape[0] != target_height or source_region.shape[1] != target_width:
            source_region = cv2.resize(source_region, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        image_display[y_start:y_end, x_start:x_end] = source_region

    # Draw measurements
    if show_measurements:
        draw_measurements()
    
    # Draw info text
    draw_info_text()
    
    cv2.imshow(window_name, image_display)
    needs_redraw = False

def draw_measurements():
    """Draw measurements on the display (separated for better performance)."""
    global image_display
    
    disp_height, disp_width = image_display.shape[:2]
    
    for i, measurement in enumerate(measurements):
        start_x, start_y = to_screen_coords(measurement["start"]["x"], measurement["start"]["y"])
        end_x, end_y = to_screen_coords(measurement["end"]["x"], measurement["end"]["y"])
        
        start_x = max(0, min(int(start_x), disp_width - 1))
        start_y = max(0, min(int(start_y), disp_height - 1))
        end_x = max(0, min(int(end_x), disp_width - 1))
        end_y = max(0, min(int(end_y), disp_height - 1))
        
        # Different colors for different measurements
        colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
        color = colors[i % len(colors)]
        
        # Draw line
        line_thickness = max(1, int(2 * zoom_factor))
        cv2.line(image_display, (start_x, start_y), (end_x, end_y), color, line_thickness)
        
        # Mark endpoints
        circle_radius = max(2, int(3 * zoom_factor))
        cv2.circle(image_display, (start_x, start_y), circle_radius, color, -1)
        cv2.circle(image_display, (end_x, end_y), circle_radius, color, -1)
        
        # Display text (only if zoom is sufficient for readability)
        if zoom_factor > 0.3:
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            
            text_lines = [f"#{measurement['id']}: {measurement['pixel_length']:.1f}px"]
            if measurement.get("real_world_length"):
                unit = measurement["reference_object"].get("unit", "mm")
                text_lines.append(f"{measurement['real_world_length']:.1f}{unit}")
            
            font_scale = max(0.4, 0.5 * zoom_factor)
            thickness = max(1, int(1 * zoom_factor))
            
            for j, text in enumerate(text_lines):
                text_y = mid_y - 10 + j * 15
                cv2.putText(image_display, text, (mid_x, text_y), 
                           cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)

def draw_info_text():
    """Draw info text in corner."""
    info_text = [
        f"Zoom: {zoom_factor:.2f}x",
        f"Measurements: {len(measurements)}",
        f"CPU Opt: ON"
    ]
    
    for i, text in enumerate(info_text):
        cv2.putText(image_display, text, (10, 20 + i * 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

def get_save_path():
    """Generate file path for measurements based on image name."""
    if current_image_path:
        base_name = os.path.splitext(os.path.basename(current_image_path))[0]
        return f"{base_name}_measurements.json"
    return "measurements.json"

def save_measurements():
    """Save measurements to JSON file."""
    if not measurements:
        return
    
    data = {
        "image_path": current_image_path,
        "image_size": {"width": image.shape[1], "height": image.shape[0]} if image is not None else None,
        "created": datetime.now().isoformat(),
        "measurements": measurements
    }
    
    filename = get_save_path()
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    print(f"Measurements saved to: {filename}")

def load_measurements():
    """Load measurements from JSON file."""
    global measurements, needs_redraw
    filename = get_save_path()
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            measurements = data.get("measurements", [])
            needs_redraw = True
            print(f"Measurements loaded: {len(measurements)} entries")
        except Exception as e:
            print(f"Error loading measurements: {e}")

def toggle_measurements():
    """Toggle measurement display on/off."""
    global show_measurements, needs_redraw
    show_measurements = not show_measurements
    needs_redraw = True
    update_display()
    print(f"Measurements {'shown' if show_measurements else 'hidden'}")

def delete_last_measurement():
    """Delete the last measurement."""
    global measurements, points, needs_redraw
    if measurements:
        deleted = measurements.pop()
        if len(points) >= 2:
            points.pop()
            points.pop()
        needs_redraw = True
        update_display()
        save_measurements()
        print(f"Measurement #{deleted['id']} deleted.")
    else:
        print("No measurements to delete.")

def show_measurement_list():
    """Show list of all measurements."""
    if not measurements:
        print("No measurements available.")
        return
    
    print(f"\n=== Measurements for {os.path.basename(current_image_path)} ===")
    for m in measurements:
        print(f"\nMeasurement #{m['id']}:")
        print(f"  Pixel length: {m['pixel_length']:.2f} px")
        if m.get("real_world_length"):
            unit = m["reference_object"].get("unit", "mm")
            print(f"  Real length: {m['real_world_length']:.2f} {unit}")
        if m.get("reference_object"):
            print(f"  Reference: {m['reference_object']['name']}")
        else:
            print(f"  Reference: None (pixel only)")
        if m.get("scale_factor"):
            unit = m["reference_object"].get("unit", "mm")
            print(f"  Scale: 1 px = {m['scale_factor']:.4f} {unit}")

def save_image():
    """Save the annotated image."""
    if image_display is not None:
        root = tk.Tk()
        root.withdraw()
        default_name = f"{os.path.splitext(os.path.basename(current_image_path))[0]}_annotated.png"
        file_path = filedialog.asksaveasfilename(
            defaultextension='.png', 
            initialname=default_name,
            filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg')]
        )
        if file_path:
            cv2.imwrite(file_path, image_display)
            print(f"Annotated image saved: {file_path}")
    else:
        print("No image to save.")

def export_measurements():
    """Export measurements as CSV for further analysis."""
    if not measurements:
        print("No measurements to export.")
        return
    
    root = tk.Tk()
    root.withdraw()
    default_name = f"{os.path.splitext(os.path.basename(current_image_path))[0]}_measurements.csv"
    file_path = filedialog.asksaveasfilename(
        defaultextension='.csv',
        initialname=default_name,
        filetypes=[('CSV', '*.csv')]
    )
    
    if file_path:
        import csv
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['ID', 'Pixel_Length', 'Real_Length', 'Unit', 'Reference_Object', 'Scale_Factor', 'Start_X', 'Start_Y', 'End_X', 'End_Y', 'Timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for m in measurements:
                row = {
                    'ID': m['id'],
                    'Pixel_Length': m['pixel_length'],
                    'Real_Length': m.get('real_world_length', ''),
                    'Unit': m['reference_object'].get('unit', '') if m.get('reference_object') else '',
                    'Reference_Object': m['reference_object'].get('name', '') if m.get('reference_object') else 'None',
                    'Scale_Factor': m.get('scale_factor', ''),
                    'Start_X': m['start']['x'],
                    'Start_Y': m['start']['y'],
                    'End_X': m['end']['x'],
                    'End_Y': m['end']['y'],
                    'Timestamp': m['timestamp']
                }
                writer.writerow(row)
        print(f"Measurements exported as CSV: {file_path}")

def reset_view():
    """Reset zoom and position."""
    global zoom_factor, offset_x, offset_y, needs_redraw, cached_scaled_image, cached_zoom
    zoom_factor = 1.0
    offset_x = 0
    offset_y = 0
    cached_scaled_image = None
    cached_zoom = 0
    needs_redraw = True
    update_display()
    print("View reset.")

def main():
    """Main program function."""
    global window_name
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(window_name, mouse_callback)

    print("=== OSINT Measurement Tool (CPU Optimized) ===")
    print("\nControls:")
    print("  'l': Load image")
    print("  Left click: Set measurement points (2 points = 1 measurement)")
    print("  Ctrl + Mouse wheel: Zoom around mouse position")
    print("  Ctrl + Left click + Drag: Pan image")
    print("  't': Toggle measurement display")
    print("  'd': Delete last measurement")
    print("  'm': Show measurement list")
    print("  's': Save annotated image")
    print("  'e': Export measurements as CSV")
    print("  'r': Reset view")
    print("  'q': Quit program")
    print("\nPerformance optimizations:")
    print("  - Cached image scaling")
    print("  - Throttled updates during panning")
    print("  - Adaptive interpolation methods")
    print("  - Reduced unnecessary redraws")
    print("\nAvailable reference objects:")
    for obj in REFERENCE_OBJECTS.keys():
        if obj != "Custom":
            data = REFERENCE_OBJECTS[obj]
            if "diameter" in data:
                print(f"  - {obj}: ⌀{data['diameter']}{data['unit']}")
            else:
                print(f"  - {obj}: {data.get('length', 'N/A')}×{data.get('width', 'N/A')}{data['unit']}")
    print("\nNote: Reference objects are optional - you can save pixel-only measurements too!")

    # Create empty window
    empty_img = np.zeros((400, 600, 3), dtype=np.uint8)
    cv2.putText(empty_img, "Press 'l' to load an image", (50, 200), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.imshow(window_name, empty_img)

    while True:
        key = cv2.waitKey(1) & 0xFF
        if key == ord('l'):
            load_image()
        elif key == ord('t'):
            toggle_measurements()
        elif key == ord('d'):
            delete_last_measurement()
        elif key == ord('m'):
            show_measurement_list()
        elif key == ord('s'):
            save_image()
        elif key == ord('e'):
            export_measurements()
        elif key == ord('r'):
            reset_view()
        elif key == ord('q'):
            print("Program terminated.")
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
