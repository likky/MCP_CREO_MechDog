#ifndef PROCMPST_EXT_BY_CON_H
#define PROCMPST_EXT_BY_CON_H

/*
   Creo Parametric TOOLKIT declarations related to cmpstExtByCon feature.
*/



#include <ProFeature.h>
#include <ProParamval.h>

PRO_BEGIN_C_DECLS

/*****************************************************************************
 Feature element tree :
 ----------------------
 |--PRO_E_FEATURE_TYPE
 |--PRO_E_STD_FEATURE_NAME
 |--PRO_E_CMPST_EBC_CHANGED_PLY
 |--PRO_E_AREA_BOUNDARY
 |  |--PRO_E_AREA_BOUNDARY_LOOPS
 |     |--PRO_E_AREA_BOUNDARY_LOOP
 |        |--PRO_E_STD_LOOP_COLLECTION_APPL
 |--PRO_E_DSGNTAREA_CREATION_FLIP


Feature elements table
---------------------------------------------------------------------------------------------------------------
Element Id                     Element Name         Data Type               Valid Values
---------------------------------------------------------------------------------------------------------------
PRO_E_FEATURE_TYPE             Feature Type         PRO_VALUE_TYPE_INT      PRO_FEAT_CMPST_PLY_EXT_BY_CON
PRO_E_STD_FEATURE_NAME         Featname             PRO_VALUE_TYPE_WSTRING  Wide character string
PRO_E_CMPST_EBC_CHANGED_PLY    Ply                  ProReference            Ply object
PRO_E_AREA_BOUNDARY            Boundary             Compound
PRO_E_AREA_BOUNDARY_LOOPS      Inner Loops          ProArray of Inner loop
PRO_E_AREA_BOUNDARY_LOOP       Inner loop           Compound
PRO_E_STD_LOOP_COLLECTION_APPL Boundary chains      PRO_VALUE_TYPE_POINTER  See ProCrvcollection.h
PRO_E_DSGNTAREA_CREATION_FLIP  Creation Flip        PRO_VALUE_TYPE_INT      Optional. 0/1



*****************************************************************************/

PRO_END_C_DECLS

#endif
