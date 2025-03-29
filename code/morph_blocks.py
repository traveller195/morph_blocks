"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from typing import Any, Optional

from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterExtent,
)
from qgis import processing


class MorphBlocks(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    EXTENT = "EXTENT"
    BUFFER_VALUE = "BUFFER_VALUE"
    OUTPUT_CENTROIDS = "OUTPUT_CENTROIDS"
    OUTPUT_BUFFER = "OUTPUT_BUFFER"

    def name(self) -> str:
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "morph_blocks"

    def displayName(self) -> str:
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return "Morph Blocks"

    def group(self) -> str:
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return "Morphology"

    def groupId(self) -> str:
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "morphology"

    def shortHelpString(self) -> str:
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it.
        """
        return "Groups building footprints into building blocks."

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It should be a polygon 
        # dataset.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                "Input building footprint layer",
                [QgsProcessing.SourceType.TypeVectorPolygon],
            )
        )

        # Add a spatial extent for the processing
        self.addParameter(
            QgsProcessingParameterExtent(
                self.EXTENT,
                "Spatial extent for the processing",
            )
        )
        
        # Add a spatial extent for the processing
        self.addParameter(
            QgsProcessingParameterNumber(
                self.BUFFER_VALUE,
                "Buffer value in meters"
            )
        )
        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, "Output block layer")
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT_CENTROIDS, "Output centroid layer", optional=True)
        )
        
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT_BUFFER, "Output buffer layer", optional=True)
        )
    def processAlgorithm(
        self,
        parameters: dict[str, Any],
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback,
    ) -> dict[str, Any]:
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsVectorLayer(parameters, self.INPUT, context)

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            source.fields(),
            source.wkbType(),
            source.sourceCrs(),
        )

        # Send some information to the user
        feedback.pushInfo(f"CRS is {source.sourceCrs().authid()}")

        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSinkError method to return a standard
        # helper text for when a sink cannot be evaluated
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))
            
        buffer_value = self.parameterAsInt(parameters, self.BUFFER_VALUE, context)
        spatial_extent = self.parameterAsExtent(parameters, self.EXTENT, context)
            
        # -------------------------------   
        # P R O C E S S I N G - S T E P S
        # ------------------------------- 
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
            
        # -------------------------------   
        # Execute "geometry repair" on input building dataset
        # -------------------------------
        feedback.pushInfo("geometry repair")
        repaired = processing.run("native:fixgeometries", {
            'INPUT': source,
            'METHOD':1,
            'OUTPUT':'TEMPORARY_OUTPUT'
        })["OUTPUT"]
        # because of dict output --> add ["OUTPUT"]
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
            
        # -------------------------------   
        # Clip input building layer to given spatial extent
        # -------------------------------
        feedback.pushInfo("clip building footprints")
        clipped = processing.run("native:extractbyextent", {
            'INPUT':repaired,
            'EXTENT':spatial_extent,
            'CLIP':False,
            'OUTPUT':'TEMPORARY_OUTPUT'
        })['OUTPUT']
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Transform CRS to metric Web Mercator (EPSG: 3857) - only if required
        # -------------------------------
        feedback.pushInfo("project CRS")
        
        transformed = processing.run("native:reprojectlayer", {
            'INPUT':clipped,
            'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:3857'),
            'CONVERT_CURVED_GEOMETRIES':False,
            'OPERATION':'+proj=noop',
            'OUTPUT':'TEMPORARY_OUTPUT'
        })['OUTPUT']
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Dissolve all building polygon footprints
        # -------------------------------
        feedback.pushInfo("dissolve all building footprints")
        
        dissolved_1 = processing.run("native:dissolve", {
            'INPUT':transformed,
            'FIELD':[],
            'SEPARATE_DISJOINT':False,
            'OUTPUT':'TEMPORARY_OUTPUT'
        })['OUTPUT']

        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Buffer with given buffer value NEGATIVE (inside)
        # -------------------------------
        feedback.pushInfo("starting buffer")
        buffer_1 = processing.run("native:buffer", {
            'INPUT':dissolved_1,
            'DISTANCE':-buffer_value,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'SEPARATE_DISJOINT':False,
            'OUTPUT':'TEMPORARY_OUTPUT'},
            feedback=feedback
            )['OUTPUT']

        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Buffer with given buffer value POSITIVE (outside)
        # -------------------------------
        feedback.pushInfo("starting buffer")
        buffer_2 = processing.run("native:buffer", {
            'INPUT':buffer_1,
            'DISTANCE':buffer_value,
            'SEGMENTS':5,
            'END_CAP_STYLE':0,
            'JOIN_STYLE':0,
            'MITER_LIMIT':2,
            'DISSOLVE':False,
            'SEPARATE_DISJOINT':False,
            'OUTPUT':'TEMPORARY_OUTPUT'},
            feedback=feedback
            )['OUTPUT']
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Create centroid (on surface) for each origin building footprint - including building id
        # -------------------------------
        feedback.pushInfo("create centroid")
        
        centroids = processing.run("native:pointonsurface", {
            'INPUT':transformed,
            'ALL_PARTS':False,
            'OUTPUT':'TEMPORARY_OUTPUT'
        })['OUTPUT']

        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Join buffer id to centroid 
        # -------------------------------
        feedback.pushInfo("join buffer id to centroid")
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Join buffer id to origin building footprint - using centroid
        # -------------------------------
        feedback.pushInfo("join buffer id to origin building footprint")
        
        centroid_with_buffer_id = processing.run("native:joinattributesbylocation", {
            'INPUT':centroids,
            'PREDICATE':[0,1,2,3,4,5,6],
            'JOIN':buffer_2,
            'JOIN_FIELDS':['fid'],
            'METHOD':0,
            'DISCARD_NONMATCHING':False,
            'PREFIX':'buffer_',
            'OUTPUT':'TEMPORARY_OUTPUT'
        })['OUTPUT']

        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Dissolve origin building footprint by buffer id
        # -------------------------------
        feedback.pushInfo("dissolve origin building footprint by buffer id")
        
        dissolved_2 = processing.run("native:dissolve", {
            'INPUT':centroid_with_buffer_id,
            'FIELD':['buffer_fid'],
            'SEPARATE_DISJOINT':False,
            'OUTPUT':'TEMPORARY_OUTPUT'
        })['OUTPUT']
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Add column "holes_count" with number of inner holes
        # -------------------------------
        feedback.pushInfo("add column holes_count")
        
        dissolved_3 = processing.run("native:addfieldtoattributestable", {
            'INPUT':dissolved_2, 
            'FIELD_NAME':'holes_count',
            'FIELD_TYPE':0,
            'FIELD_LENGTH':10,
            'FIELD_PRECISION':0,
            'FIELD_ALIAS':'',
            'FIELD_COMMENT':'',
            'OUTPUT':'TEMPORARY_OUTPUT'
        })['OUTPUT']
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # -------------------------------   
        # Add column "holes_total_area" with total area of inner holes
        # -------------------------------
        feedback.pushInfo("add column holes_total_area")
        dissolved_3 = processing.run("native:addfieldtoattributestable", {
            'INPUT':dissolved_2, 
            'FIELD_NAME':'holes_count',
            'FIELD_TYPE':0,
            'FIELD_LENGTH':10,
            'FIELD_PRECISION':0,
            'FIELD_ALIAS':'',
            'FIELD_COMMENT':'',
            'OUTPUT':'TEMPORARY_OUTPUT'
        })['OUTPUT']
        
        if feedback.isCanceled():
            feedback.pushInfo("Script was canceled.")
            return
        # Compute the number of steps to display within the progress bar and
        # get features from source
        #total = 100.0 / source.featureCount() if source.featureCount() else 0
        #features = source.getFeatures()

        #for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
        #    if feedback.isCanceled():
        #        break

            # Add a feature in the sink
        #    sink.addFeature(feature, QgsFeatureSink.Flag.FastInsert)

            # Update the progress bar
        #    feedback.setProgress(int(current * total))

        # To run another Processing algorithm as part of this algorithm, you can use
        # processing.run(...). Make sure you pass the current context and feedback
        # to processing.run to ensure that all temporary layer outputs are available
        # to the executed algorithm, and that the executed algorithm can send feedback
        # reports to the user (and correctly handle cancellation and progress reports!)
        if False:
            buffered_layer = processing.run(
                "native:buffer",
                {
                    "INPUT": dest_id,
                    "DISTANCE": 1.5,
                    "SEGMENTS": 5,
                    "END_CAP_STYLE": 0,
                    "JOIN_STYLE": 0,
                    "MITER_LIMIT": 2,
                    "DISSOLVE": False,
                    "OUTPUT": "memory:",
                },
                context=context,
                feedback=feedback,
            )["OUTPUT"]

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: dest_id}

    def createInstance(self):
        return self.__class__()
