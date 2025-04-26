# Geospatial Conversion System 🌍

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A powerful tool for converting geographic coordinates, performing Mercator projections, and creating interactive maps with address lookup capabilities.

## Features ✨

- **Coordinate Management**
  - Interactive coordinate input
  - CSV file support (appends new coordinates)
  - Automatic validation (-90° to 90° lat, -180° to 180° lon)

- **Projection System**
  - Forward Mercator projection
  - Reverse projection verification
  - High precision (6 decimal places)

- **Geocoding**
  - Nominatim API integration
  - Smart caching system
  - Rate-limited requests (1/sec)

- **Visualization**
  - Interactive Folium maps
  - 2D/3D view switching
  - Connection lines between points
  - Marker popups with projection details

## Installation 🛠️

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/geospatial-converter.git
   cd geospatial-converter
   ## Screenshots

### Terminal Output
![Terminal](screenshots/terminal_output.png)

### Interactive Map
![Map](screenshots/interactive_map.png)

### Processed Data
![CSV](screenshots/csv_data.png)