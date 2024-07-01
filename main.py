from fastapi import FastAPI, File, UploadFile
from typing import List
import json

app = FastAPI()

def parse_edi_file(file_content):
    lines = file_content.splitlines()
    parsed_data = [line.strip().replace('~', '').split('*') for line in lines]
    return parsed_data

def convert_to_json(parsed_data):
    edi_dict = {
        "heading": {
            "transaction_set_header_ST": {},
            "beginning_segment_for_inventory_inquiry_advice_BIA": {},
            "reference_identification_REF": []
        },
        "detail": {
            "item_identification_LIN_loop": []
        },
        "summary": {
            "transaction_totals_CTT": {},
            "transaction_set_trailer_SE": {}
        }
    }

    for i, segment in enumerate(parsed_data):
        if segment[0] == 'ST':
            edi_dict["heading"]["transaction_set_header_ST"] = {
                "transaction_set_identifier_code_01": segment[1],
                "transaction_set_control_number_02": int(segment[2])
            }
        elif segment[0] == 'BIA':
            edi_dict["heading"]["beginning_segment_for_inventory_inquiry_advice_BIA"] = {
                "transaction_set_purpose_code_01": segment[1],
                "report_type_code_02": segment[2],
                "reference_identification_03": segment[3],
                "date_04": segment[4],
                "time_05": segment[5]
            }
        elif segment[0] == 'REF':
            edi_dict["heading"]["reference_identification_REF"].append({
                "reference_identification_qualifier_01": segment[1],
                "reference_identification_02": segment[2],
                "description_03": segment[3] if len(segment) > 3 else ""
            })
        elif segment[0] == 'LIN':
            article = {
                "item_identification_LIN": {
                    "assigned_identification_01": segment[1],
                    "product_service_id_qualifier_02": segment[2],
                    "product_service_id_03": segment[3],
                    "product_service_id_qualifier_04": segment[4],
                    "product_service_id_05": segment[5],
                    "product_service_id_qualifier_06": segment[6],
                    "product_service_id_07": segment[7]
                },
                "reference_identification_REF": [],
                "quantity_QTY_loop": []
            }
            # Process REF and QTY segments within LIN
            j = i + 1
            while j < len(parsed_data) and parsed_data[j][0] in ['REF', 'QTY']:
                if parsed_data[j][0] == 'REF':
                    article["reference_identification_REF"].append({
                        "reference_identification_qualifier_01": parsed_data[j][1],
                        "reference_identification_02": parsed_data[j][2]
                    })
                elif parsed_data[j][0] == 'QTY':
                    qty = {
                        "quantity_QTY": {
                            "quantity_qualifier_01": parsed_data[j][1],
                            "quantity_02": int(parsed_data[j][2])
                        },
                        "measurements_MEA": [],
                        "date_time_reference_DTM_196": [],
                        "date_time_reference_DTM_197": []
                    }
                    article["quantity_QTY_loop"].append(qty)
                j += 1
            edi_dict["detail"]["item_identification_LIN_loop"].append(article)
        elif segment[0] == 'CTT':
            edi_dict["summary"]["transaction_totals_CTT"] = {
                "number_of_line_items_01": int(segment[1])
            }
        elif segment[0] == 'SE':
            edi_dict["summary"]["transaction_set_trailer_SE"] = {
                "number_of_included_segments_01": int(segment[1]),
                "transaction_set_control_number_02": int(segment[2])
            }

    return json.dumps(edi_dict, indent=4)

@app.post("/parse-edi/")
async def parse_edi(files: List[UploadFile] = File(...)):
    results = []
    for file in files:
        content = await file.read()
        parsed_data = parse_edi_file(content.decode('utf-8'))
        json_data = convert_to_json(parsed_data)
        results.append({
            "filename": file.filename,
            "data": json.loads(json_data)
        })
    return results
