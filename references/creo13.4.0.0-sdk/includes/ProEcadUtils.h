

#ifndef PROECADUTILS_H_
#define PROECADUTILS_H_

#include <ProSizeConst.h>
#include <ProObjects.h>

typedef enum {
   PRO_TK_ECAD_IDX
  ,PRO_TK_ECAD_EDA
  ,PRO_TK_ECAD_IDF3
} ProTKEcadType;

typedef enum {
   PRO_TK_ECAD_HOLES_CREATE_METHOD_FEATURE
  ,PRO_TK_ECAD_HOLES_CREATE_METHOD_LW_FEATURE
  ,PRO_TK_ECAD_HOLES_CREATE_METHOD_NOT_CREATE
} ProTKEcadImpHolesCreateMethod;

typedef void* ProEcadImpOpts;

typedef void* ProEcadExpOpts;

PRO_BEGIN_C_DECLS

extern ProError ProEcadImport(ProPath         filename,
                              ProEcadImpOpts  options,
                              ProTKEcadType   ecad_type,
                              ProMdl         *r_new_model);
/*
  Purpose: Import an EDMD design to specified type

  Input Arguments:
     filename        - Name of the file to be imported.
     options         - Import options.
     ecad_type       - The type of the imported file.
                       EDMD (*.idx) and IDF (*.emn) file formats
                       are supported.

  Output Arguments:
     r_new_model     - The new assembly that Creo Parametric created.

  Return Values:
     PRO_TK_NO_ERROR      - Import finished successfully.
     PRO_TK_INVALID_NAME  - The file name is NULL or
                            extension of file name is invalid
     PRO_TK_INVALID_DIR   - The directory of file name is invalid
     PRO_TK_EMPTY         - The file is empty.
     PRO_TK_UNSUPPORTED   - ecad_type is not supported.
     PRO_TK_USER_ABORT    - Used in collaboration mode.
     PRO_TK_BAD_INPUTS    - One of the inputs has bad value which
                            is not of the above errors.
     PRO_TK_CONTINUE      - Import succeeded with errors or warnings.
     PRO_TK_GENERAL_ERROR - Import failed for any other reason.
*/

extern ProError ProEcadExport(ProPath               filename,
                              ProEcadExpOpts        options,
                              ProTKEcadType         ecad_type,
                              ProMdl                assem_model);
/*
  Purpose: Export ECAD Assembly design into EDMD or EDA format.

  Input Arguments:
     filename        - Name of the output file to be exported.
     options         - Reserved for future expansion. Pass NULL.
     ecad_type       - The type of the exported file.
                       EDMD (*.idx) and IDF (*.emn) file formats
                       are supported.
     assem_model     - The assembly to be exported.

  Output Arguments:
     none.

  Return Values:
     PRO_TK_NO_ERROR        - Export finished successfully.
     PRO_TK_INVALID_NAME    - The file name is NULL or
                              extension of file name is invalid
     PRO_TK_INVALID_DIR     - The directory of file name is invalid or
                              is read only
     PRO_TK_UNSUPPORTED     - ecad_type is not supported.
     PRO_TK_NOT_IMPLEMENTED - options parameter is not NULL.
     PRO_TK_USER_ABORT      - Used in collaboration mode.
     PRO_TK_BAD_INPUTS      - One of the inputs has bad value which
                              is not of the above errors.
     PRO_TK_GENERAL_ERROR   - Export failed for any other reason.
*/

extern ProError ProEcadImpOptsAlloc( ProEcadImpOpts *options );
/*
  Purpose:
     Allocates the handle for a <i>ProEcadImpOpts</i> data structure.

  Input Arguments:
     None

  Output Arguments:
     options   - The pointer to the handle for the <i>ProEcadImpOpts</i> 
                 structure. You should free this memory when you are 
                 done using it.

  Return Values:

     PRO_TK_NO_ERROR   - The function successfully allocated the handle.
     PRO_TK_BAD_INPUTS - if input is NULL pointer 
*/

extern ProError ProEcadImpOptsFree( ProEcadImpOpts *options );
/*
  Purpose:
     Releases the handle to the <i>ProEcadImpOpts</i> data structure.

  Input Arguments:
     options   - The pointer to the handle for the <i>ProEcadImpOpts</i>

  Output Arguments:
     None

  Return Values:
    
     PRO_TK_NO_ERROR   - The function successfully freed the handle.
     PRO_TK_BAD_INPUTS - if input is NULL pointer 

*/

extern ProError ProEcadImpOptsFlexDesignSet (ProEcadImpOpts options,
                                             ProBoolean     flex_design);
/*
  Purpose:
     Sets the import options to be according to flexible or rigid PCB design
     needs.

  Input Arguments:
     options      - The pointer to the handle for the <i>ProEcadImpOpts</i>
     flex_design  - Import the PCB design as flexible (PRO_B_TRUE) or as
                    Rigid (PRO_B_FALSE)

  Output Arguments:
     None

  Return Values:
     PRO_TK_NO_ERROR    - The function successfully set the options.
     PRO_TK_BAD_INPUTS  - One or more input arguments is invalid.
*/

extern ProError ProEcadImpOptsFlexDesignGet (ProEcadImpOpts  options,
                                             ProBoolean     *r_flex_design);
/* 
  Purpose:
     Collect the current options settings to check if they are according to
     flexible PCB design needs.

  Input Arguments:
     options     - The pointer to the handle for the <i>ProEcadImpOpts</i>.

  Output Arguments:
     r_flex_design  - The current import options settings match/do not match
                      flexible PCB design.

  Return Values:
     PRO_TK_NO_ERROR      - The function successfully retrieved the information.
     PRO_TK_BAD_INPUTS    - One or more input arguments is invalid.
*/

extern ProError ProEcadImpHolesAddDiamRange( ProEcadImpOpts                options,
                                             double                        diam_lower_bound,
                                             double                        diam_upper_bound,
                                             ProTKEcadImpHolesCreateMethod create_method );
/* 
  Purpose:
     Set holes import creation method for all holes in a given diameter range.

  Input Arguments:
     options           - The pointer to the handle for the
	                     <i>ProEcadImpOpts</i>.
	 diam_lower_bound  - Diameter lower bound (-1.0 for unbounded).
	 diam_upper_bound  - Diameter upper bound (-1.0 for unbounded). 
	 create_method     - Hole creation method
	                     <i>ProTKEcadImpHolesCreateMethod<i>.

  Output Arguments:
     None
	 
  Return Values:
     PRO_TK_NO_ERROR      - The function successfully retrieved the information.
     PRO_TK_BAD_INPUTS    - One or more input arguments is invalid.
*/

extern ProError ProEcadImpOptsIDF3EmpFileNameSet(
                                      ProEcadImpOpts options,
                                      ProPath        idf_emp_filename);
/*
  Purpose:
     Sets the import option EMP file name for IDF3 import.

  Input Arguments:
     options           - The pointer to the handle for the <i>ProEcadImpOpts</i>
     idf_emp_filename  - Name of the input EMP file.

  Output Arguments:
     None

  Return Values:
     PRO_TK_NO_ERROR      - Finished successfully.
     PRO_TK_BAD_INPUTS    - One of the inputs has bad value which
                            is not of the above errors.
*/

extern ProError ProEcadImpOptsIDF3ImpOtherOutlineSet(
    ProEcadImpOpts options,
    ProBoolean     import_other_outline);
/*
  Purpose:
     Sets the import option import other outlines for IDF3 import.

  Input Arguments:
     options                - The pointer to the handle for the <i>ProEcadImpOpts</i>
     import_other_outlines  - Import IDF3 with (PRO_B_TRUE) or without
                              (PRO_B_FALSE) Other outline objects.

  Output Arguments:
     None

  Return Values:
     PRO_TK_NO_ERROR      - Finished successfully.
     PRO_TK_BAD_INPUTS    - One of the inputs has bad value which
                            is not of the above errors.
*/

extern ProError ProEcadGetChanges(ProPath filename);
/*
  Purpose:
    Apply the changes from an incremental IDX input file into the current
    ECAD assembly design.

  Input Arguments:
     filename        - Name of the input incremental IDX file.

   Output Arguments:
      None

  Return Values:
     PRO_TK_NO_ERROR      - Finished successfully.
     PRO_TK_NO_LICENSE    - In case of a license error.
     PRO_TK_E_NOT_FOUND   - In case the input file name does not exist.
     PRO_TK_NOT_VALID     - In case the Get changes operation is not
                            applicable for the current design.
*/

extern ProError ProEcadSendChanges(ProPath filename);
/*
  Purpose:
    Save the current ECAD assembly design changes to an incremental
    IDX output file.

  Input Arguments:
     filename        - Name of the output incremental IDX file.

   Output Arguments:
      None

  Return Values:
     PRO_TK_NO_ERROR      - Finished successfully.
     PRO_TK_NO_LICENSE    - In case of a license error.
     PRO_TK_NOT_VALID     - In case the Send changes operation is not
                            applicable for the current design.
     PRO_TK_NO_CHANGE     - In case there are no changes.
*/

PRO_END_C_DECLS

#endif /* PROECADUTILS_H_ */
