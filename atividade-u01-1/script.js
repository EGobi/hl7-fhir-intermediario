function PrepareRecord(page = 1, limit = 9999) {
    var v_patient_reference = document.getElementById('v_patient_reference').value;
    var v_prescriber_reference = document.getElementById('v_prescriber_reference').value;
    var v_prescription_code = document.getElementById('v_med_code').value;
    var v_prescription_name = document.getElementById('v_med_name').value;
    var v_prescription_date = document.getElementById('v_prescription_date').value;
    var v_dosage_instruction = document.getElementById('v_dosage_instruction').value;
    var v_patient_display = document.getElementById('v_patient_display').value;
    var v_prescriber_display = document.getElementById('v_prescriber_display').value;
    var v_status = document.getElementById('v_status').value;
    var v_intent = document.getElementById('v_intent').value;
    var result = prepareArgoMedReqRecord(v_patient_reference, v_prescriber_reference, v_prescription_code, v_prescription_name, v_prescription_date, v_dosage_instruction, v_patient_display, v_prescriber_display, v_status, v_intent)
    var v_result = document.getElementById('result');
    v_result.textContent = JSON.stringify(result);
}

function prepareArgoMedReqRecord(
    v_patient_reference,         //reference to a patient resource
    v_prescriber_reference,      //reference to a practitioner resource
    v_prescription_code,         //medication code (rxnorm)
    v_prescription_name,         //medication name (rxnorm)
    v_prescription_date,         //prescription date
    v_dosage_instruction,        //dosage instruction text
    v_patient_display,           //patient basic info
    v_prescriber_display,        //practitioner basic info
    v_status,                    //prescription lifecycle
    v_intent                     //kind of order
) {
    var myVDate = new Date(v_prescription_date); // Date from input
    var v_narrative = "<div xmlns=\"http://www.w3.org/1999/xhtml\">" +
        "<p><strong>Medication Request</strong></p>" +
        "<p><strong>status</strong>: </p>" + v_status +
        "<p><strong>intent</strong>: </p>" + v_intent +
        "<p><strong>medication</strong>: " + v_prescription_code + " - " + v_prescription_name + "</p>" +
        "<p><strong>subject</strong>: " + v_patient_display + "</p>" +
        "<p><strong>authoredOn</strong>:" + v_prescription_date + "</p>" +
        "<p><strong>requester</strong>:" + v_prescriber_display + "</p>" +
        "<p><strong>dosageInstruction</strong>:" + v_dosage_instruction + "</p><div>";
    resource =
        [{
            "resourceType": "MedicationRequest",
            "text": {
                "status": "generated",
                "div": v_narrative
            },
            "status": v_status,
            "intent": v_intent,
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": v_prescription_code,
                        "display": v_prescription_name
                    }
                ],
                "text": v_prescription_name
            },
            "subject": {
                "reference": "Patient/" + v_patient_reference,
                "display": v_patient_display
            },
            "authoredOn": myVDate.toISOString().split('T')[0],
            "requester": {
                "reference": "Practitioner/" + v_prescriber_reference,
                "display": v_prescriber_display
            },
            "dosageInstruction": [
                { "text": v_dosage_instruction }
            ]
        }
        ]
    return resource;
}