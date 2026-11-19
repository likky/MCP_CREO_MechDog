#ifndef PROCMPST_LAMINATE_ZONE_H
#define PROCMPST_LAMINATE_ZONE_H

/*
   Creo Parametric TOOLKIT declarations related to composite Laminate Zone feature.
*/



#include <ProANSI.h>

PRO_BEGIN_C_DECLS

/***********************************************************************************************

 Feature element tree :
 ----------------------
 |--PRO_E_FEATURE_TYPE
 |--PRO_E_STD_FEATURE_NAME
 |--PRO_E_CMPST_PLY_BASE_QUILT
 |--PRO_E_AREA_BOUNDARY
 |  |--PRO_E_AREA_BOUNDARY_LOOPS
 |     |--PRO_E_AREA_BOUNDARY_LOOP
 |        |--PRO_E_STD_LOOP_COLLECTION_APPL
 |
 |--PRO_E_DSGNTAREA_CREATION_FLIP
 


Feature elements table
-------------------------------------------------------------------------------------------------------
Element Id                     Element Name           Data Type                Valid Values
-------------------------------------------------------------------------------------------------------
PRO_E_FEATURE_TYPE             Feature Type           PRO_VALUE_TYPE_INT       PRO_FEAT_CMPST_LAMINATE_ZONE
PRO_E_STD_FEATURE_NAME	       featname	              PRO_VALUE_TYPE_WSTRING   Wide character string
PRO_E_CMPST_PLY_BASE_QUILT     CmpstPlyBaseQuiltStep  PRO_VALUE_TYPE_SELECTION The layup surface
PRO_E_AREA_BOUNDARY            Boundary               compound
PRO_E_AREA_BOUNDARY_LOOPS      Loops                  ProArray of Loops
PRO_E_AREA_BOUNDARY_LOOP       Loop                   compound
PRO_E_STD_LOOP_COLLECTION_APPL Boundary chains        PRO_VALUE_TYPE_POINTER   See ProCrvcollection.h
PRO_E_DSGNTAREA_CREATION_FLIP  Creation Flip          PRO_VALUE_TYPE_INT       Optional. 0/1

******************************************************************************************************/

PRO_END_C_DECLS

#endif
