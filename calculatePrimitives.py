# -*- coding: utf-8 -*-
"""
ExportLandsatSRComposite.py, SERVIR-Mekong (2017-07-30)

export landsat composites with gapfilling
________________________________________________________________________________


Usage
------

$ python  model.py {options}

{options} include:

--year (-y)      : required
                 : year to create the Landsat composite image for
                 : in format YYYY

--user (-u)      : user account used to create the composite
                 : changes the ~/.config/earthengine/credentials file
                 : dictionary is called to get credentials
                 : options are servirmekong, servir-mekong, ate, biplov .. default is servir-mekong

Example Usage
-------------

1) export surface reflectance composite for dryhot season of 2000 to assets:

  $ python model.py -y 2000 -u Quyen

"""

import ee
import logging
import time
import math
from usercredentials import addUserCredentials
import argparse
import numpy as np

class environment(object):
        
	def __init__(self):
		"""Initialize the environment."""   
         
        # Initialize the Earth Engine object, using the authentication credentials.
        #ee.Initialize()
		self.timeString = time.strftime("%Y%m%d_%H%M%S")
		
		self.assetName = "test_primitives"
		self.userID = "users/apoortinga/temp/" 
		self.pixSize = 30
		
		self.nModels = 10
		
		self.year = 0

		# Load Mekong study region (Myanmar, Thailand, Laos, Vietnam, Cambodia)
		mekongBuffer = ee.FeatureCollection('ft:1LEGeqwlBCAlN61ie5ol24NdUDqB1MgpFR_sJNWQJ');
		mekongRegion = mekongBuffer.geometry();
		self.studyArea = mekongRegion;

		self.composite = "Median"

		self.classFieldName = 'land_class';
		
		self.modelType = 'RF'
		#self.modelType = 'SVM'
		#self.modelType = 'per'
		#self.modelType = 'nav'
		
		self.exportName = 'allcomposite2015_'  + self.modelType + self.composite + str(self.nModels)



class indices():

	def __init__(self):
		
		# list with functions to call for each index
		self.functionList = {"ND_blue_green" : self.ND_blue_green, \
							 "ND_blue_red" : self.ND_blue_red, \
							 "ND_blue_nir" : self.ND_blue_nir, \
							 "ND_blue_swir1" : self.ND_blue_swir1, \
							 "ND_blue_swir2" : self.ND_blue_swir2, \
							 "ND_green_red" : self.ND_green_red, \
							 "ND_green_nir" : self.ND_green_nir, \
							 "ND_green_swir1" : self.ND_green_swir1, \
							 "ND_green_swir2" : self.ND_green_swir2, \
							 "ND_red_swir1" : self.ND_red_swir1, \
							 "ND_red_swir2" : self.ND_red_swir2, \
							 "ND_nir_red" : self.ND_nir_red, \
							 "ND_nir_swir1" : self.ND_nir_swir1, \
							 "ND_nir_swir2" : self.ND_nir_swir2, \
							 "ND_swir1_swir2" : self.ND_swir1_swir2, \
							 "R_swir1_nir" : self.R_swir1_nir, \
							 "R_red_swir1" : self.R_red_swir1, \
							 "EVI" : self.EVI, \
							 "SAVI" : self.SAVI, \
							 "IBI" : self.IBI}


	def addAllTasselCapIndices(self,img): 
		""" Function to get all tasselCap indices """
		
		def getTasseledCap(img):
			"""Function to compute the Tasseled Cap transformation and return an image"""
			logging.info('get tasselcap for computed images')
			
			coefficients = ee.Array([
				[0.3037, 0.2793, 0.4743, 0.5585, 0.5082, 0.1863],
				[-0.2848, -0.2435, -0.5436, 0.7243, 0.0840, -0.1800],
				[0.1509, 0.1973, 0.3279, 0.3406, -0.7112, -0.4572],
				[-0.8242, 0.0849, 0.4392, -0.0580, 0.2012, -0.2768],
				[-0.3280, 0.0549, 0.1075, 0.1855, -0.4357, 0.8085],
				[0.1084, -0.9022, 0.4120, 0.0573, -0.0251, 0.0238]
			]);
		
			bands=ee.List(['blue','green','red','nir','swir1','swir2'])
			
			# Make an Array Image, with a 1-D Array per pixel.
			arrayImage1D = img.select(bands).toArray()
		
			# Make an Array Image with a 2-D Array per pixel, 6x1.
			arrayImage2D = arrayImage1D.toArray(1)
		
			componentsImage = ee.Image(coefficients).matrixMultiply(arrayImage2D).arrayProject([0]).arrayFlatten([['brightness', 'greenness', 'wetness', 'fourth', 'fifth', 'sixth']]).float();
	  
			# Get a multi-band image with TC-named bands.
			return img.addBands(componentsImage);	
			
			
		def addTCAngles(img):

			""" Function to add Tasseled Cap angles and distances to an image. Assumes image has bands: 'brightness', 'greenness', and 'wetness'."""
		
			logging.info('add tasseled cap angles')
		
			# Select brightness, greenness, and wetness bands	
			brightness = img.select('brightness');
			greenness = img.select('greenness');
			wetness = img.select('wetness');
	  
			# Calculate Tasseled Cap angles and distances
			tcAngleBG = brightness.atan2(greenness).divide(math.pi).rename(['tcAngleBG']);
			tcAngleGW = greenness.atan2(wetness).divide(math.pi).rename(['tcAngleGW']);
			tcAngleBW = brightness.atan2(wetness).divide(math.pi).rename(['tcAngleBW']);
			tcDistBG = brightness.hypot(greenness).rename(['tcDistBG']);
			tcDistGW = greenness.hypot(wetness).rename(['tcDistGW']);
			tcDistBW = brightness.hypot(wetness).rename(['tcDistBW']);
			img = img.addBands(tcAngleBG).addBands(tcAngleGW).addBands(tcAngleBW).addBands(tcDistBG).addBands(tcDistGW).addBands(tcDistBW);
			
			return img;
	
	
		img = getTasseledCap(img)
		img = addTCAngles(img)
		return img

	def ND_blue_green(self,img):
		img = img.addBands(img.normalizedDifference(['blue','green']).rename(['ND_blue_green']));
		return img
	
	def ND_blue_red(self,img):
		img = img.addBands(img.normalizedDifference(['blue','red']).rename(['ND_blue_red']));
		return img
	
	def ND_blue_nir(self,img):
		img = img.addBands(img.normalizedDifference(['blue','nir']).rename(['ND_blue_nir']));
		return img
	
	def ND_blue_swir1(self,img):
		img = img.addBands(img.normalizedDifference(['blue','swir1']).rename(['ND_blue_swir1']));
		return img
	
	def ND_blue_swir2(self,img):
		img = img.addBands(img.normalizedDifference(['blue','swir2']).rename(['ND_blue_swir2']));
		return img

	def ND_green_red(self,img):
		img = img.addBands(img.normalizedDifference(['green','red']).rename(['ND_green_red']));
		return img
	
	def ND_green_nir(self,img):
		img = img.addBands(img.normalizedDifference(['green','nir']).rename(['ND_green_nir']));  # NDWBI
		return img
	
	def ND_green_swir1(self,img):
		img = img.addBands(img.normalizedDifference(['green','swir1']).rename(['ND_green_swir1']));  # NDSI, MNDWI
		return img
	
	def ND_green_swir2(self,img):
		img = img.addBands(img.normalizedDifference(['green','swir2']).rename(['ND_green_swir2']));
		return img
		
	def ND_red_swir1(self,img):
		img = img.addBands(img.normalizedDifference(['red','swir1']).rename(['ND_red_swir1']));
		return img
			
	def ND_red_swir2(self,img):
		img = img.addBands(img.normalizedDifference(['red','swir2']).rename(['ND_red_swir2']));
		return img

	def ND_nir_red(self,img):
		img = img.addBands(img.normalizedDifference(['nir','red']).rename(['ND_nir_red']));  # NDVI
		return img
	
	def ND_nir_swir1(self,img):
		img = img.addBands(img.normalizedDifference(['nir','swir1']).rename(['ND_nir_swir1']));  # NDWI, LSWI, -NDBI
		return img
	
	def ND_nir_swir2(self,img):
		img = img.addBands(img.normalizedDifference(['nir','swir2']).rename(['ND_nir_swir2']));  # NBR, MNDVI
		return img

	def ND_swir1_swir2(self,img):
		img = img.addBands(img.normalizedDifference(['swir1','swir2']).rename(['ND_swir1_swir2']));
		return img
  
	def R_swir1_nir(self,img):
		# Add ratios
		img = img.addBands(img.select('swir1').divide(img.select('nir')).rename(['R_swir1_nir']));  # ratio 5/4
		return img
			
	def R_red_swir1(self,img):
		img = img.addBands(img.select('red').divide(img.select('swir1')).rename(['R_red_swir1']));  # ratio 3/5
		return img

	def EVI(self,img):
		#Add Enhanced Vegetation Index (EVI)
		evi = img.expression(
			'2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))', {
			  'NIR': img.select('nir'),
			  'RED': img.select('red'),
			  'BLUE': img.select('blue')
		  }).float();
	
		img = img.addBands(evi.rename(['EVI']));

		return img
	  
	def SAVI(self,img):
		# Add Soil Adjust Vegetation Index (SAVI)
		# using L = 0.5;
		savi = img.expression(
			'(NIR - RED) * (1 + 0.5)/(NIR + RED + 0.5)', {
			  'NIR': img.select('nir'),
			  'RED': img.select('red')
		  }).float();
		img = img.addBands(savi.rename(['SAVI']));

		return img
	  
	def IBI(self,img):
		# Add Index-Based Built-Up Index (IBI)
		ibi_a = img.expression(
			'2*SWIR1/(SWIR1 + NIR)', {
			  'SWIR1': img.select('swir1'),
			  'NIR': img.select('nir')
			}).rename(['IBI_A']);
	

		ibi_b = img.expression(
			'(NIR/(NIR + RED)) + (GREEN/(GREEN + SWIR1))', {
			  'NIR': img.select('nir'),
			  'RED': img.select('red'),
			  'GREEN': img.select('green'),
			  'SWIR1': img.select('swir1')
			}).rename(['IBI_B']);
		
		ibi_a = ibi_a.addBands(ibi_b);
		ibi = ibi_a.normalizedDifference(['IBI_A','IBI_B']);
		img = img.addBands(ibi.rename(['IBI']));
		
		return img


class primitives():
	
	def __init__(self):
		"""Initialize the Surfrace Reflectance app."""  
        
		# import the log library
		import logging
	
		# get the environment
		self.env = environment()
		
		# get object with indices
		self.indices = indices() 
	
	def importData(self):
		print "import data"

	def getIndices(self,img,covariates):	
		""" add indices to image"""
		
		# no need to add indices that are already there
		indices = self.removeDuplicates(covariates,img.bandNames().getInfo())
		
		for item in indices:
			img = self.indices.functionList[item](img)

		return img
		
	def createPrimitive(self,spring,summer,autumn,winter,trainingDataSet,y):
		""" calculate the primitive """ 

		covariates = ["ND_blue_green","ND_blue_red","ND_blue_nir","ND_blue_swir1","ND_blue_swir2","ND_green_red","ND_green_nir","ND_green_swir1","ND_green_swir2","ND_red_swir1","ND_red_swir2","ND_nir_red","ND_nir_swir1","ND_nir_swir2","ND_swir1_swir2","R_swir1_nir","R_red_swir1","EVI","SAVI","IBI"]

		spring = self.ScaleBands(spring)
		spring = self.indices.addAllTasselCapIndices(spring)
		spring = self.getIndices(spring,covariates)

		summer = self.ScaleBands(summer)
		summer = self.indices.addAllTasselCapIndices(summer)
		summer = self.getIndices(summer,covariates)

		autumn = self.ScaleBands(autumn)
		autumn = self.indices.addAllTasselCapIndices(autumn)
		autumn = self.getIndices(autumn,covariates)

		winter = self.ScaleBands(winter)
		winter = self.indices.addAllTasselCapIndices(winter)
		winter = self.getIndices(winter,covariates)
		
		# Get the JRC water 
		water = ee.Image('JRC/GSW1_0/GlobalSurfaceWater').mask(ee.Image(1));
		
		# rename the bands

		spring = self.renameImageBands(spring,"spring") 
		autumn = self.renameImageBands(autumn,"autumn") 
		summer = self.renameImageBands(summer,"summer") 
		winter = self.renameImageBands(winter,"winter") 

		# construct the composites
		composite = spring.addBands(summer).addBands(autumn).addBands(winter).addBands(water);
		composite = self.addTopography(composite);
		composite = self.addJRC(composite)
		
		allIndices = ["ND_blue_green","ND_blue_red","ND_blue_nir","ND_blue_swir1", \
			   "ND_blue_swir2","ND_green_red","ND_green_nir","ND_green_swir1", \
			   "ND_green_swir2","ND_red_swir1","ND_red_swir2","ND_nir_red", \
			   "ND_nir_swir1","ND_nir_swir2","ND_swir1_swir2","R_swir1_nir",
			   "R_red_swir1","EVI","SAVI","IBI", \
			   "blue","green","red","nir","swir1","swir2",\
			   "blue_stdDev","green_stdDev","red_stdDev","nir_stdDev",\
			   "swir1_stdDev","swir2_stdDev","ND_nir_swir2_stdDev",\
			   "ND_green_swir1_stdDev","ND_nir_red_stdDev","thermal",\
			   "thermal_stdDev",'brightness','greenness','wetness',\
			   'tcAngleBG','tcAngleGW','tcAngleBW','tcDistBG','tcDistGW'
			   ]	
			   
		jrcBands = ['occurrence','change_abs','change_norm','seasonality','transition','max_extent']
		elevationBands = ['eastness','northness','elevation','slope','aspect']
		nightLights = ['stable_lights']			   
			   	
		# combine all training bands
		trainingBands = self.renameBands(allIndices,"spring") + self.renameBands(allIndices,"summer") + self.renameBands(allIndices,"autumn") + self.renameBands(allIndices,"winter") + jrcBands + elevationBands # 
		# select training bands
		composite = composite.select(trainingBands)
		
		classNames = ee.List(["water","imperv","forest","fieldcrops","olives","citrus","riperean","dade","barren","snow"]);

		# run the model		
		classification = self.getBaggedModel(composite, \
						     trainingDataSet, \
						     composite.bandNames(), \
						     self.env.nModels, \
						     self.env.classFieldName, \
						     classNames, \
						     self.env.modelType);
		# export the classification

		self.ExportToAsset(self.env.exportName,classification)
		
	def addTopography(self,img):
		"""  Function to add 30m SRTM elevation and derived slope, aspect, eastness, and 
		northness to an image. Elevation is in meters, slope is between 0 and 90 deg,
		aspect is between 0 and 359 deg. Eastness and northness are unitless and are
		between -1 and 1. """

		# Import SRTM elevation data
		elevation = ee.Image("USGS/SRTMGL1_003");
		
		# Calculate slope, aspect, and hillshade
		topo = ee.Algorithms.Terrain(elevation);
		
		# From aspect (a), calculate eastness (sin a), northness (cos a)
		deg2rad = ee.Number(math.pi).divide(180);
		aspect = topo.select(['aspect']);
		aspect_rad = aspect.multiply(deg2rad);
		eastness = aspect_rad.sin().rename(['eastness']).float();
		northness = aspect_rad.cos().rename(['northness']).float();
		
		# Add topography bands to image
		topo = topo.select(['elevation','slope','aspect']).addBands(eastness).addBands(northness);
		img = img.addBands(topo);
		return img;

	def addJRC(self,img):
		""" Function to add JRC Water layers: 'occurrence', 'change_abs', 
			'change_norm', 'seasonality','transition', 'max_extent' """
		
		jrcImage = ee.Image("JRC/GSW1_0/GlobalSurfaceWater")
		
		img = img.addBands(jrcImage.select(['occurrence']).rename(['occurrence']))
		img = img.addBands(jrcImage.select(['change_abs']).rename(['change_abs']))
		img = img.addBands(jrcImage.select(['change_norm']).rename(['change_norm']))
		img = img.addBands(jrcImage.select(['seasonality']).rename(['seasonality']))
		img = img.addBands(jrcImage.select(['transition']).rename(['transition']))
		img = img.addBands(jrcImage.select(['max_extent']).rename(['max_extent']))
		
		return img
		
	def addNightLights(self,img,y):
		""" Function to add nighlights to the composite' """
		
		startDate = ee.Date.fromYMD(y-2, 1, 1)
		endDate = ee.Date.fromYMD(y-2, 12, 31)
		
		if y < 2012:
		
			nightLights = ee.Image(ee.ImageCollection("NOAA/DMSP-OLS/NIGHTTIME_LIGHTS").filterDate(startDate,endDate).mean())	
			img = img.addBands(nightLights.select(["stable_lights"]).rename(["stable_lights"]))
		
		if y >= 2012:
			nightLights = ee.Image(ee.ImageCollection("NOAA/VIIRS/DNB/MONTHLY_V1/VCMCFG").filterDate(startDate,endDate).mean())	
			img = img.addBands(nightLights.select(["avg_rad"]).rename(["stable_lights"]))
		
		return img

	def getBaggedModel(self,image,data,bands,nModels,classFieldName,classNames,modelType):
		""" Function to perform bagged classification on an image, using either Random
			Forest or Support Vector Machines (SVM). The data is bagged such that each 
			class has the same number of observations, equal to the minimum number of 
			observations of any class. """
		
		print('Sampling WITHOUT replacement');
		
		print modelType
		
		# Find the average number of observations (avgMin = 5000/nClasses)
		nModels = ee.Number(nModels);
		nClasses = ee.Number(classNames.length())
		avgMin = ee.Number(5000).divide(nClasses).int();
		
		# Find the minimum number of observations of any class (dataMin) and use 75%
		dataCounts = data.reduceColumns(ee.Reducer.frequencyHistogram(),[classFieldName]);
		dataValues = ee.Dictionary(dataCounts.get('histogram')).values();
		dataMin = ee.Number(dataValues.reduce(ee.Reducer.min())).multiply(0.75).int();
		# The observations per class per model is the minimum of dataMin and avgMin
		dataMin = dataMin.min(avgMin);

		# For each model m, randomly sort the data
		modelList = ee.List.sequence(0,nModels.subtract(1));
		randname = 'randsort';
		
		def classifications(m):
			# Add a random column
			data_m = data.randomColumn(randname,m);
			
			#For each class k, take the first dataMin number of observations, sorted randomly
			classList = ee.List.sequence(0,nClasses.subtract(1));
			
			def mapClassList(k):
				k = ee.Number(k);
				data_k = data_m.filter(ee.Filter.equals(classFieldName,k)).limit(dataMin,randname);
			
				return data_k;
		
			data_m = classList.map(mapClassList)
		
			# Aggregate training data from each class into one collection
			data_m = ee.FeatureCollection(data_m).flatten();
    
			# Train the classifier
			if modelType == 'SVM':
				classifier = ee.Classifier.svm().train(data_m,classFieldName,bands);
			elif modelType == 'RF':
				classifier = ee.Classifier.randomForest(1,0,1,1,False,m).train(data_m,classFieldName,bands);
			elif modelType == 'per':	
				classifier = ee.Classifier.perceptron(1,True).train(data_m,classFieldName,bands);
			elif modelType == 'nav':
			    classifier = ee.Classifier.naiveBayes().train(data_m,classFieldName,bands);

    		# Run the classifier on the image
			classification = image.classify(classifier,'prediction');
    
			return classification;

		classification = modelList.map(classifications)
		classification = ee.ImageCollection(classification);
	
		classNumbers = ee.List.sequence(0,nClasses.subtract(1));
	
		def classNumber(n):
			classNumber = ee.Number(n);
			
			def imageClassification(img):
				 return img.eq(classNumber)
			
			out = classification.map(imageClassification).sum().divide(nModels);
			return out
	
		
		classProbabilities = ee.ImageCollection.fromImages(classNumbers.map(classNumber))
		
		# Convert the probabilities image collection to stack of image bands
		classProbabilitiesStack = self.newCollectionToImage(classProbabilities).rename(classNames);
      
		# Also return the mode or majority classification
		classification = classification.mode().rename(['Mode']);
		classification_image = classification.addBands(classProbabilitiesStack);
  
		return classification_image;


	def newCollectionToImage(self,collection):
		""" Helper function to convert image collection into stack of image bands"""
		
		def createStack(img,prev):
			return ee.Image(prev).addBands(img)
		
		stack = ee.Image(collection.iterate(createStack, ee.Image(1)));

		stack = stack.select(ee.List.sequence(1, stack.bandNames().size().subtract(1)));
		return stack;

       
	def removeDuplicates(self,covariateList,bands):
		""" function to remove duplicates, i.e. existing bands do not need to be calculated """
		
		return [elem for elem in covariateList if elem not in bands]

	def ScaleBands(self,img):
		"""Landsat is scaled by factor 0.0001 """
		
		thermalBand = ee.List(['thermal','thermal_stdDev'])
		gapfillBand = ee.List(['gapfill'])
		
		thermal = ee.Image(img).select(thermalBand).divide(10)
		gapfill = ee.Image(img).select(gapfillBand)
		
		otherBands = ee.Image(img).bandNames().removeAll(thermalBand)
		otherBands = otherBands.removeAll(gapfillBand)
		scaled = ee.Image(img).select(otherBands).multiply(0.0001)
		
		image = ee.Image(scaled.addBands(thermal).addBands(gapfill))
		
		return ee.Image(image.copyProperties(img))

 
	def renameImageBands(self,image,prefix):
		""" Function to add a prefix to all bands in an image """
		
		bandNames = list(image.bandNames().getInfo());
				
		newNames = []
		for band in bandNames:
			bandName = prefix + "_" + band
			newNames.append(bandName)
		
		image = image.rename(ee.List(newNames));
		return image

	def renameBands(self,bandNames,prefix):
		""" Function to add a prefix to all bands in an image """
					
		newNames = []
		for band in bandNames:
			bandName = prefix + "_" + band
			newNames.append(bandName)
		
		
		return newNames

				
	def ExportToAsset(self,name,img):  
		"""export to asset """
		
		outputName = self.env.userID + name + self.env.assetName + self.env.timeString
		logging.info('export image to asset: ' + str(outputName)) 
		#startDate = ee.Date.fromYMD(self.env.startYear,1,1)
		#endDate = ee.Date.fromYMD(self.env.endYear,12,31)    

		#image = ee.Image(img).set({'system:time_start':startDate.millis(), \
	
		region = ee.Geometry.Polygon(img.geometry().getInfo()['coordinates'])
		task_ordered = ee.batch.Export.image.toAsset(image=ee.Image(img), description=self.env.assetName, assetId=outputName,region=region['coordinates'], maxPixels=1e13,scale=self.env.pixSize)
        
        # start task
		task_ordered.start() 
		


if __name__ == "__main__":
  
	
    # set argument parsing object
	parser = argparse.ArgumentParser(description="Create primitive composite using Google Earth Engine.")
   
	parser.add_argument('--year','-y', type=str,required=True, \
                        help="Year to perform the ats correction and save to asset format in 'YYYY'")

	parser.add_argument('--user','-u', type=str, default="servir-mekong",choices=['servir-mekong','servirmekong',"ate","biplov","quyen","atesig"], \
						help="specify user account to run task")
						
	args = parser.parse_args() # get arguments  
  
	# user account to run task on
	userName = args.user
	year = int(args.year)
	#self.env.year = year

	# create a new file in ~/.config/earthengine/credentials with token of user
	addUserCredentials(userName)

	ee.Initialize()
	
	env = environment()
    
	# import the images
	spring = ee.Image("users/apoortinga/JordanImagery/spring2015_2015Median")
	summer = ee.Image("users/apoortinga/JordanImagery/summer2015_2015Median")
	autumn = ee.Image("users/apoortinga/JordanImagery/autumn2015_2015Median")
	winter = ee.Image("users/apoortinga/JordanImagery/winter2014_2015Median")
	

	trainingData = ee.FeatureCollection("ft:1JraWVeRWoiyHgi7zN0lTMJQL80X8GwOHwwcFXqez")

	primitives().createPrimitive(spring,summer,autumn,winter,trainingData,2015)#,selectedBandsMedoid )

