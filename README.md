# morph_blocks
Create a cityblock based on historical building footprint dataset using morph tools

- this project is started on code sprint of FOSSGIS 2025 in Muenster, Germany.
- aim is to code an QGIS plugin

Method:
- load polygon buidling footprint dataset
- dissolve all building footprints
- buffer with a negative / minus value
- buffer with a positive and equal value
- create centroid on surface for origin building dataset
- join id of buffered polygons to centroid
- dissolve origin building footprints by buffer id
- add attribute with count of inner holes
- add attribute with total area of inner holes


dataset
- **GIS Dataset Nürnberg War Damage Maps WWII** https://fd-repo.uni-bamberg.de/records/he14f-xh380

tutorial
- https://www.qgistutorials.com/de/docs/3/processing_python_plugin.html
- 
