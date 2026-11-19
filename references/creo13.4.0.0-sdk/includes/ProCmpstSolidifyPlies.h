#ifndef PROCMPSTSOLIDIFYPLIES_H
#define PROCMPSTSOLIDIFYPLIES_H

/*
   Creo Parametric TOOLKIT declarations related to Solidify Plies feature.
*/



#include <ProToolkit.h>

/*****************************************************************************\

1. Feature element tree:

  PRO_E_FEATURE_TREE
  |
  |--PRO_E_FEATURE_TYPE
  |
  |--PRO_E_STD_FEATURE_NAME
  |
  |--PRO_E_OPT_CREATE_IML
  |
  |--PRO_E_OPT_CREATE_DROPOFF
  |
  |--PRO_E_OPT_KEEP_SKIRTS

  (2) Feature elements table:

  -------------------------------------------------------------------------------------------------
  Element Id               Element Name             Data Type                Valid Values
  -------------------------------------------------------------------------------------------------
  PRO_E_FEATURE_TYPE       Feature Type             PRO_VALUE_TYPE_INT       PRO_FEAT_PLY_SOLIDIFY
  PRO_E_STD_FEATURE_NAME   Feature Name             PRO_VALUE_TYPE_WSTRING   Name unique among features
  PRO_E_OPT_CREATE_IML     Create IML attribute     PRO_VALUE_TYPE_BOOLEAN   PRO_B_TRUE, PRO_B_FALSE
  PRO_E_OPT_CREATE_DROPOFF Create Dropoff attribute PRO_VALUE_TYPE_BOOLEAN   PRO_B_TRUE, PRO_B_FALSE
  PRO_E_OPT_KEEP_SKIRTS    Keep Skirts attribute    PRO_VALUE_TYPE_BOOLEAN   PRO_B_TRUE, PRO_B_FALSE (see Note)
  -------------------------------------------------------------------------------------------------

(3) Note

  The element PRO_E_OPT_KEEP_SKIRTS is valid only when
  PRO_E_OPT_CREATE_DROPOFF element is set to PRO_B_TRUE.
  Value assigned to PRO_E_OPT_KEEP_SKIRTS element when
  the PRO_E_OPT_CREATE_DROPOFF element is set to PRO_B_FALSE
  will be ignored.

\*****************************************************************************/

#endif /* PROCMPSTSOLIDIFYPLIES_H */
