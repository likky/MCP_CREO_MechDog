#ifndef PRODTMREFH
#define PRODTMREFH



#include <ProANSI.h>

PRO_BEGIN_C_DECLS


/*****************************************************************************\

Feature element tree
 
   PRO_E_FEATURE_TREE
     |
     |--PRO_E_FEATURE_TYPE
     |
     |--PRO_E_STD_FEATURE_NAME
     |
     |--PRO_E_REFS_FT_TYPE    
     |
     |--PRO_E_DTMREF_CONTEXT   
     |
     |--PRO_E_STD_SURF_COLLECTION_APPL

**************************************************************************/

/*
Feature elements table
------------------------------------------------------------------------------
Element Id                       Element Name        Data Type
------------------------------------------------------------------------------
PRO_E_FEATURE_TYPE               Feature Type        PRO_VALUE_TYPE_INT
PRO_E_STD_FEATURE_NAME           Feature Name        PRO_VALUE_TYPE_WSTRING
PRO_E_REFS_FT_TYPE               Feature sub-type    PRO_VALUE_TYPE_INT
PRO_E_DTMREF_CONTEXT             Context type        PRO_VALUE_TYPE_INT
PRO_E_STD_SURF_COLLECTION_APPL   References          PRO_VALUE_TYPE_SELECTION
*/

/*
PRO_E_FEATURE_TYPE               PRO_FEAT_REFERENCE
PRO_E_STD_FEATURE_NAME           
PRO_E_REFS_FT_TYPE               See Pro_Dtmref_Type
PRO_E_DTMREF_CONTEXT             See Pro_Dtmref_Context
PRO_E_STD_SURF_COLLECTION_APPL   
*/

typedef enum pro_dtmref_type
{
  PRO_DTMREF_SURFACE            = 1
} Pro_Dtmref_Type;

typedef enum pro_dtmref_context
{
  PRO_DTMREF_LOCAL              = -1,
  PRO_DTMREF_INCONTEXT          = 10
} Pro_Dtmref_Context;


PRO_END_C_DECLS

#endif
