from flask import Flask, request, jsonify
from shapely.geometry import shape, mapping
from pystac_client import Client


app = Flask(__name__)

# In-memory database
fields_db = []
images_db = []

# API endpoint to retrieve the newest image from a polygon
@app.route('/api/get_newest_image', methods=['POST'])
def get_newest_image():
    data = request.json
    polygon_geojson = data.get('polygon')

    # Convert GeoJSON to Shapely Polygon
    polygon = shape(polygon_geojson)

    # Check if the image is in the database
    image = find_image_in_database(polygon)

    if image:
        return jsonify({'image_url': image['url'], 'source': 'database'})
    else:
        # If not in the database, fetch from the 3rd party API using pystac-client
        image_url = fetch_image_from_3rd_party(polygon)
        if image_url:
            # Add the new image to the database
            images_db.append({'polygon': polygon, 'url': image_url})

            # Fetch the image content and return it as part of the API response
            return jsonify({'image_url': image_url, 'source': '3rd_party'})
        else:
            return jsonify({'error': 'Failed to fetch image from 3rd party API'}), 500

# API endpoint to store field data including the boundary/geometry
@app.route('/api/store_field', methods=['POST'])
def store_field():
    data = request.json
    field_geojson = data.get('polygon')

    # Convert GeoJSON to Shapely Polygon
    field_polygon = shape(field_geojson)

    # Add the field to the database
    fields_db.append({'polygon': field_polygon})
    
    return jsonify({'message': 'Field data stored successfully'})

# API endpoint to retrieve all fields that intersect with the given polygon
@app.route('/api/get_intersecting_fields', methods=['POST'])
def get_intersecting_fields():
    data = request.json
    search_polygon_geojson = data.get('polygon')

    # Convert GeoJSON to Shapely Polygon
    search_polygon = shape(search_polygon_geojson)

    # Find intersecting fields
    intersecting_fields = find_intersecting_fields(search_polygon)

    # Convert Shapely Polygons to GeoJSON format
    intersecting_fields_geojson = [mapping(poly) for poly in intersecting_fields]
    return jsonify({'intersecting_fields': intersecting_fields_geojson})

# Function to find the newest image in the database for a given polygon
def find_image_in_database(polygon):
    for image in images_db:
        if image['polygon'].intersects(polygon):
            return image
    return None

# Function to fetch the newest image from the 3rd party API using pystac-client
def fetch_image_from_3rd_party(polygon):

    # Use pystac-client to search for items within the given polygon
    client = Client.open("https://earth-search.aws.element84.com/v1")
    search = client.search(
        collections=['sentinel-2-l2a'],
        bbox=polygon.bounds
    )
    
    # Get the first matching item
    item = next(search.items())
    asset = item.assets["thumbnail"]
    # Extract the URL of the first item
    if item:
        return asset.href
    else:
        return None

# Function to find fields that intersect with a given polygon
def find_intersecting_fields(search_polygon):
    intersecting_fields = []
    for field in fields_db:
        if field['polygon'].intersects(search_polygon):
            intersecting_fields.append(field['polygon'])
    return intersecting_fields

if __name__ == '__main__':
    app.run(debug=True)
