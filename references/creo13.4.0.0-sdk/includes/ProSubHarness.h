#ifndef PROSUBHARNESS_H
#define PROSUBHARNESS_H

/*
   Creo Parametric TOOLKIT declarations related to Subharness feature.
*/



#include <ProFeature.h>
#include <ProParamval.h>
#include <ctstrutils_macros.h>

PRO_BEGIN_C_DECLS

/*****************************************************************************
Subharness feature element tree :
 ----------------------
 |--PRO_E_FEATURE_TYPE
 |--PRO_E_STD_FEATURE_NAME
 |--PRO_E_SUBHARN_CABLES_REF


Subharness feature elements table :
------------------------------------------------------------------------
Element Id                  Element Name         Data Type
------------------------------------------------------------------------
PRO_E_FEATURE_TYPE         Feature Type          int (PRO_FEAT_SUBHARNESS)
PRO_E_STD_FEATURE_NAME	   Featname	             PRO_VALUE_TYPE_WSTRING
PRO_E_SUBHARN_CABLES_REF	 Cables reference      ProArray of ProReference



*****************************************************************************/



PRO_END_C_DECLS

#endif  /* PROSUBHARNESS_H */
