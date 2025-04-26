# Import required libraries
import csv
import math
import folium
import pandas as pd
import webbrowser
import json
import time
from pathlib import Path
from colorama import Fore, init
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from folium.plugins import MousePosition, Fullscreen
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize colorama for colored terminal output
init(autoreset=True)

# Cache configuration for storing geocoding results
CACHE_FILE = "geo_cache.json"
cache = {}  # In-memory cache dictionary

def load_cache():
    """Load geocoding cache from JSON file"""
    global cache
    try:
        if Path(CACHE_FILE).exists():
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
    except Exception as e:
        print(f"{Fore.YELLOW}Cache loading failed: {str(e)}")

def save_cache():
    """Save current cache state to JSON file"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"{Fore.YELLOW}Cache saving failed: {str(e)}")

def input_coordinates_interactively():
    """Collect and validate coordinates through interactive CLI"""
    print(f"\n{Fore.CYAN}Enter coordinates (latitude,longitude), one per line.")
    print(f"{Fore.YELLOW}Type 'done' when finished, 'exit' to cancel")
    
    coordinates = []
    while True:
        entry = input(f"{Fore.WHITE}▶ ").strip()
        
        if entry.lower() == 'done':
            return coordinates
        if entry.lower() == 'exit':
            print(f"{Fore.YELLOW}Canceling input...")
            return None
        
        try:
            lat, lon = map(float, entry.split(','))
            if not (-90 <= lat <= 90):
                print(f"{Fore.RED}Latitude must be between -90 and 90")
                continue
            if not (-180 <= lon <= 180):
                print(f"{Fore.RED}Longitude must be between -180 and 180")
                continue
            coordinates.append((lat, lon))
            print(f"{Fore.GREEN}Added: {lat:.4f}, {lon:.4f}")
        except Exception as e:
            print(f"{Fore.RED}Invalid input: {str(e)}")
            print(f"{Fore.YELLOW}Correct format: 12.3456,98.7654")

def save_to_csv(coordinates, filename="coordinates.csv"):
    """Append coordinates to CSV file preserving existing data"""
    try:
        file_exists = Path(filename).exists()
        
        with open(filename, 'a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['latitude', 'longitude'])
            writer.writerows(coordinates)
            
        print(f"{Fore.GREEN}Added {len(coordinates)} coordinates to {filename}")
        return True
    except Exception as e:
        print(f"{Fore.RED}Failed to save coordinates: {str(e)}")
        return False

def batch_geocode(coordinates):
    """Batch geocoding with caching and rate limiting"""
    geolocator = Nominatim(
        user_agent="geo_app_optimized/1.0 (your@email.com)",
        timeout=15
    )
    reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1.1)

    new_coords = []
    for lat, lon in coordinates:
        cache_key = f"{round(lat, 4):.4f},{round(lon, 4):.4f}"
        if cache_key not in cache:
            new_coords.append((lat, lon, cache_key))

    if not new_coords:
        return {}

    print(f"\n{Fore.CYAN}Geocoding {len(new_coords)} coordinates (~{len(new_coords)} seconds)...")

    start_time = time.time()
    processed = 0
    last_update = 0

    def process_coord(lat, lon, key):
        try:
            location = reverse((lat, lon))
            return key, location.address if location else "Not found"
        except Exception as e:
            return key, f"Error: {str(e)}"

    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = [
            executor.submit(process_coord, lat, lon, key)
            for lat, lon, key in new_coords
        ]

        for future in as_completed(futures):
            key, result = future.result()
            cache[key] = result
            processed += 1
            
            if time.time() - last_update > 5:
                elapsed = time.time() - start_time
                remaining = (len(new_coords) - processed) * 1.1
                print(f"{Fore.CYAN}Processed {processed}/{len(new_coords)} "
                      f"[{elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining]")
                last_update = time.time()

    save_cache()
    print(f"{Fore.GREEN}Geocoding completed in {time.time() - start_time:.1f} seconds")
    
    return {
        (round(lat, 4), round(lon, 4)): cache.get(f"{round(lat, 4):.4f},{round(lon, 4):.4f}", "Error")
        for lat, lon in coordinates
    }

def create_optimized_map(data):
    """Generate interactive Folium map with multiple features"""
    avg_lat = sum(lat for lat, *_ in data) / len(data)
    avg_lon = sum(lon for _, lon, *_ in data) / len(data)

    m = folium.Map(
        location=[avg_lat, avg_lon],
        zoom_start=5,
        tiles='OpenStreetMap',
        control_scale=True
    )

    folium.TileLayer(
        tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        name='3D Terrain',
        attr='OpenTopoMap',
        show=False
    ).add_to(m)

    fg = folium.FeatureGroup(name='Coordinates')
    
    for lat, lon, x, y, rev_lat, rev_lon, address in data:
        popup = f"""
        <div style="width:250px">
            <b>{address}</b><hr>
            <div style="font-size:12px">
                <b>Original:</b> {lat:.6f}°, {lon:.6f}°<br>
                <b>Projected:</b> X={x:.2f}, Y={y:.2f}<br>
                <b>Reversed:</b> {rev_lat:.6f}°, {rev_lon:.6f}°
            </div>
        </div>
        """
        folium.Marker(
            [lat, lon],
            popup=popup,
            icon=folium.Icon(color='blue', icon='map-marker')
        ).add_to(fg)

    folium.PolyLine(
        [[lat, lon] for lat, lon, *_ in data],
        color='blue',
        weight=1,
        opacity=0.5
    ).add_to(fg)

    fg.add_to(m)

    MousePosition(position='bottomleft').add_to(m)
    Fullscreen(position='topright').add_to(m)
    folium.LayerControl(position='topleft', collapsed=False).add_to(m)

    return m

def mercator_projection(lat, lon):
    """Convert WGS84 coordinates to Mercator projection"""
    lat = max(min(lat, 89.9), -89.9)
    R = 6371000/637.1
    return (
        R * math.radians(lon),
        R * math.log(math.tan(math.pi/4 + math.radians(lat)/2))
    )

def inverse_mercator(x, y):
    """Convert Mercator projection back to WGS84 coordinates"""
    R = 6371000/637.1
    return (
        math.degrees(2 * math.atan(math.exp(y/R)) - math.pi/2),
        math.degrees(x/R)
    )

def main():
    """Main program execution flow"""
    print(f"{Fore.CYAN}\nInteractive Geospatial Converter")
    print(f"{Fore.YELLOW}===============================\n")
    
    try:
        print(f"{Fore.CYAN}Would you like to add new coordinates? (y/n): ", end='')
        if input().strip().lower() == 'y':
            new_coords = input_coordinates_interactively()
            if new_coords:
                if not save_to_csv(new_coords):
                    raise ValueError("Failed to save coordinates")
                else:
                    print(f"{Fore.CYAN}Existing coordinates preserved, new ones added")
            else:
                print(f"{Fore.YELLOW}No new coordinates added")
        
        load_cache()
        
        try:
            df = pd.read_csv("coordinates.csv")
        except FileNotFoundError:
            raise ValueError("Coordinates file not found. Please create 'coordinates.csv' or use interactive input")

        df.columns = df.columns.str.lower()

        lat_col = next((c for c in df.columns if 'lat' in c), None)
        lon_col = next((c for c in df.columns if 'lon' in c), None)
        if not lat_col or not lon_col:
            raise ValueError("Latitude/Longitude columns not found")

        coords = list(zip(df[lat_col], df[lon_col]))
        
        address_map = {}
        print(f"{Fore.CYAN}Enable address lookup? (y/n): ", end='')
        if input().strip().lower() == 'y':
            # Use rounded coordinates for deduplication
            unique_coords = list({(round(lat, 4), round(lon, 4)) for lat, lon in coords})
            address_map = batch_geocode(unique_coords)
        
        output_data = []
        for lat, lon in coords:
            try:
                lat = float(lat)
                lon = float(lon)
                if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                    print(f"{Fore.YELLOW}Skipping invalid coordinates: {lat}, {lon}")
                    continue

                x, y = mercator_projection(lat, lon)
                rev_lat, rev_lon = inverse_mercator(x, y)
                
                # Get address using rounded cache key
                cache_key = f"{round(lat, 4):.4f},{round(lon, 4):.4f}"
                address = cache.get(cache_key, "Address lookup disabled")
                
                output_data.append((
                    lat, lon,
                    x, y,
                    rev_lat, rev_lon,
                    address
                ))

            except Exception as e:
                print(f"{Fore.YELLOW}Skipping invalid row: {str(e)}")
                continue

        result_df = pd.DataFrame(output_data,
                               columns=['Latitude', 'Longitude',
                                        'X', 'Y',
                                        'Reversed_Lat', 'Reversed_Lon',
                                        'Address'])
        result_df.to_csv("converted_coordinates.csv", index=False)

        print(f"{Fore.GREEN}\nCreating interactive map...")
        create_optimized_map(output_data).save("geo_map.html")
        
        print(f"{Fore.CYAN}\nOutput files created:")
        print(f"- Converted coordinates: converted_coordinates.csv")
        print(f"- Interactive map: geo_map.html")
        webbrowser.open("geo_map.html")

    except Exception as e:
        print(f"\n{Fore.RED}ERROR: {str(e)}")
    
    finally:
        save_cache()
        print(f"\n{Fore.CYAN}Process completed")

if __name__ == "__main__":
    main()