#ifndef PROCMPST_PLIES_TRANS_H
#define PROCMPST_PLIES_TRANS_H

/*
   Creo Parametric TOOLKIT declarations related to CmpstPliesTrans feature.
*/



#include <ProFeature.h>
#include <ProParamval.h>

PRO_BEGIN_C_DECLS

/*****************************************************************************
CmpstPliesTrans feature element tree :
 ----------------------
 |--PRO_E_FEATURE_TYPE
 |--PRO_E_STD_FEATURE_NAME
 |--PRO_E_CMPST_PLIES_TRANS_DIM
 |--PRO_E_CMPST_PLIES_TRANS_TYPE
 |--PRO_E_CMPST_PLIES_TRANS_REFS
 |--PRO_E_CMPST_PLIES_TRANS_OFFS_ARR
 |  |--PRO_E_CMPST_PLIES_TRANS_ARR_CMPD
 |  |  |--PRO_E_CMPST_PLIES_TRANS_PLY_REF_ARR
 |  |  |--PRO_E_CMPST_PLIES_TRANS_OFF_ARR
 |--PRO_E_STD_CURVE_COLLECTION_APPL
 |--PRO_E_CMPST_PLIES_TRANS_PAT_SETT
 |--PRO_E_CMPST_PLIES_TRANS_DIST_SETT
 |--PRO_E_CMPST_PLIES_TRANS_OFFSET
 |--PRO_E_CMPST_PLIES_TRANS_ANG_OFFSET
 |--PRO_E_CMPST_PLIES_TRANS_AXIS_REF



CmpstPliesTrans feature elements table :
----------------------------------------------------------------------------------------------------------------------------------------------
Element Id                              Element Name         Data Type                                    Valid Values                     Notes
----------------------------------------------------------------------------------------------------------------------------------------------
PRO_E_FEATURE_TYPE	                    Feature Type	    PRO_VALUE_TYPE_INT	                          PRO_FEAT_CMPST_PLIES_TRANS
PRO_E_STD_FEATURE_NAME	                featname	        PRO_VALUE_TYPE_WSTRING
PRO_E_CMPST_PLIES_TRANS_DIM	            Dimension Scheme	ProCmpst_plies_transOffset_type
PRO_E_CMPST_PLIES_TRANS_TYPE	        transition_type	    ProCmpst_plies_transTransition_type
PRO_E_CMPST_PLIES_TRANS_REFS	        plies_refs	        ProArray of ProReference                                                       Note 1
PRO_E_CMPST_PLIES_TRANS_OFFS_ARR        offsets_arr     	ProArray of ProCmpst_plies_transOffsets_cmpd                                   Note 2
PRO_E_CMPST_PLIES_TRANS_ARR_CMPD        offsets_cmpd	    ProCmpst_plies_transOffsets_cmpd
PRO_E_CMPST_PLIES_TRANS_PLY_REF_ARR	    plies_ref     	    ProReference
PRO_E_CMPST_PLIES_TRANS_OFF_ARR	        offset_arr_col	    PRO_VALUE_TYPE_DOUBLE
PRO_E_STD_CURVE_COLLECTION_APPL	        transition_ref	    ProCollection
PRO_E_CMPST_PLIES_TRANS_PAT_SETT        pattern_settings	ProCmpst_plies_transPattern_settings
PRO_E_CMPST_PLIES_TRANS_DIST_SETT       distance_settings       ProCmpst_plies_transDistance_settings
PRO_E_CMPST_PLIES_TRANS_OFFSET	        offset	            PRO_VALUE_TYPE_DOUBLE
PRO_E_CMPST_PLIES_TRANS_ANG_OFFSET	    angular_offset	    PRO_VALUE_TYPE_DOUBLE
PRO_E_CMPST_PLIES_TRANS_AXIS_REF	    Axis	            ProReference



Notes:
1. PRO_E_CMPST_PLIES_TRANS_REFS is visible only when PRO_E_CMPST_PLIES_TRANS_TYPE is PRO_CMPST_PLIES_TRANS_TRANSITION_TYPE_PATTERN.
2. PRO_E_CMPST_PLIES_TRANS_OFFS_ARR is visible only when PRO_E_CMPST_PLIES_TRANS_TYPE is PRO_CMPST_PLIES_TRANS_TRANSITION_TYPE_CUSTOM.

*****************************************************************************/

typedef enum
{
    PRO_CMPST_PLIES_TRANS_OFFSET_TYPE_LINEAR = 1,
    PRO_CMPST_PLIES_TRANS_OFFSET_TYPE_ANGULAR = 2,
}ProCmpst_plies_transOffset_type;

typedef enum
{
    PRO_CMPST_PLIES_TRANS_TRANSITION_TYPE_PATTERN = 1,
    PRO_CMPST_PLIES_TRANS_TRANSITION_TYPE_CUSTOM = 2,
}ProCmpst_plies_transTransition_type;

typedef enum
{
    PRO_CMPST_PLIES_TRANS_PATTERN_SETTINGS_BACKSLASH = 1,
    PRO_CMPST_PLIES_TRANS_PATTERN_SETTINGS_SLASH = 2,
}ProCmpst_plies_transPattern_settings;

typedef enum
{
  PRO_CMPST_PLIES_TRANS_DISTANCE_SETTINGS_3D_DISTANCE      = 1,
  PRO_CMPST_PLIES_TRANS_DISTANCE_SETTINGS_SURFACE_DISTANCE = 2,
} ProCmpst_plies_transDistance_settings;

PRO_END_C_DECLS

#endif
