#ifndef PROEXT_BY_REF_H
#define PROEXT_BY_REF_H

/*
   Creo Parametric TOOLKIT declarations related to extByRef feature.
*/



#include <ProFeature.h>
#include <ProParamval.h>

PRO_BEGIN_C_DECLS

/*****************************************************************************
 Feature element tree :
 ----------------------
 |--PRO_E_FEATURE_TYPE
 |--PRO_E_STD_FEATURE_NAME
 |--PRO_E_CMPST_EXT_PLY_REF
 |--PRO_E_CMPST_EXT_RM_CMPND
 |  |--PRO_E_STD_CURVE_COLLECTION_APPL
 |--PRO_E_CMPST_EXT_NEW_CMPND 
 |  |--PRO_E_STD_CURVE_COLLECTION_APPL


Feature elements table
------------------------------------------------------------------------
Element Id                      Element Name                  Data Type
------------------------------------------------------------------------
PRO_E_FEATURE_TYPE              Feature Type                  int (PRO_FEAT_CMPST_PLY_EXT_BY_REF)
PRO_E_STD_FEATURE_NAME	        Featname	                    PRO_VALUE_TYPE_WSTRING
PRO_E_CMPST_EXT_PLY_REF	        Ply	ProReference
PRO_E_CMPST_EXT_RM_CMPND	      Extension references compound	Compound
PRO_E_STD_CURVE_COLLECTION_APPL	Extension references	        ProCollection
PRO_E_CMPST_EXT_NEW_CMPND 	    Up to compound	              Compound
PRO_E_STD_CURVE_COLLECTION_APPL	Up to references	            ProCollection



*****************************************************************************/



PRO_END_C_DECLS

#endif

