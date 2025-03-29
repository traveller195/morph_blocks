"""
Model exported as python.
Name : Modell
Group : 
With QGIS : 34201
"""

from typing import Any, Optional

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingFeedback, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsCoordinateReferenceSystem
from qgis import processing


class Modell(QgsProcessingAlgorithm):

    def initAlgorithm(self, config: Optional[dict[str, Any]] = None):
        self.addParameter(QgsProcessingParameterString('layername', 'Layername', multiLine=False, defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('rohdaten', 'Rohdaten', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))

    def processAlgorithm(self, parameters: dict[str, Any], context: QgsProcessingContext, model_feedback: QgsProcessingFeedback) -> dict[str, Any]:
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(7, model_feedback)
        results = {}
        outputs = {}

        # Räumlichen Index erzeugen
        alg_params = {
            'INPUT': parameters['rohdaten']
        }
        outputs['RumlichenIndexErzeugen'] = processing.run('native:createspatialindex', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Geometrien reparieren
        alg_params = {
            'INPUT': outputs['RumlichenIndexErzeugen']['OUTPUT'],
            'METHOD': 1,  # Struktur
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GeometrienReparieren'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Rechter-Hand-Regel erzwingen
        alg_params = {
            'INPUT': outputs['GeometrienReparieren']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['RechterhandregelErzwingen'] = processing.run('native:forcerhr', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Layer in Projekt laden
        alg_params = {
            'INPUT': outputs['RechterhandregelErzwingen']['OUTPUT'],
            'NAME': 'test'
        }
        outputs['LayerInProjektLaden'] = processing.run('native:loadlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Geometrietyp umwandeln
        alg_params = {
            'INPUT': outputs['RechterhandregelErzwingen']['OUTPUT'],
            'TYPE': 4,  # Polygons
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GeometrietypUmwandeln'] = processing.run('qgis:convertgeometrytype', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Layer reprojizieren
        alg_params = {
            'CONVERT_CURVED_GEOMETRIES': True,
            'INPUT': outputs['GeometrietypUmwandeln']['OUTPUT'],
            'OPERATION': None,
            'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:25832'),
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['LayerReprojizieren'] = processing.run('native:reprojectlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Layer in Projekt laden
        alg_params = {
            'INPUT': outputs['LayerReprojizieren']['OUTPUT'],
            'NAME': parameters['layername']
        }
        outputs['LayerInProjektLaden'] = processing.run('native:loadlayer', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        return results

    def name(self) -> str:
        return 'Modell'

    def displayName(self) -> str:
        return 'Modell'

    def group(self) -> str:
        return ''

    def groupId(self) -> str:
        return ''

    def createInstance(self):
        return self.__class__()
