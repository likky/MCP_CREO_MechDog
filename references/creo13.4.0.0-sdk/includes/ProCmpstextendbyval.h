#ifndef PRO_CMPSTEXTENDBYVAL_H
#define PRO_CMPSTEXTENDBYVAL_H

/*
   Creo Parametric TOOLKIT declarations related to boundExtend feature.
*/



#include <ProFeature.h>
#include <ProParamval.h>

PRO_BEGIN_C_DECLS

/*****************************************************************************
 Feature element tree :
 ----------------------
 |--PRO_E_FEATURE_TYPE
 |--PRO_E_STD_FEATURE_NAME
 |--PRO_E_EXT_PLY_REF
 |--PRO_E_STD_CURVE_COLLECTION_APPL
 |--PRO_E_EXTENDED_VAL


Feature elements table
------------------------------------------------------------------------
Element Id                  Element Name         Data Type
------------------------------------------------------------------------
PRO_E_FEATURE_TYPE         Feature Type          int (PRO_FEAT_CMPST_PLY_EXT_BY_VAL)
PRO_E_STD_FEATURE_NAME	Featname	PRO_VALUE_TYPE_WSTRING
PRO_E_EXT_PLY_REF	Ply	ProReference
PRO_E_STD_CURVE_COLLECTION_APPL	Extension references	ProCollection
PRO_E_EXTENDED_VAL	Value	PRO_VALUE_TYPE_DOUBLE



*****************************************************************************/



PRO_END_C_DECLS

#endif

