import os
import json
import zipfile
import requests
import urllib3
import time

# SSL xəbərdarlıqlarını söndürürük
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# GitHub Actions mühitindən dəyişənləri alırıq
QRADAR_HOST = os.environ.get("QRADAR_HOST")
SEC_TOKEN = os.environ.get("QRADAR_SEC_TOKEN")
RULES_DIR = "rules/"
ZIP_FILENAME = "soc_rules_extension.zip"

def create_xml_from_json():
    print("JSON faylları oxunur və XML formatına çevrilir...")
    
    # QRadar üçün XML şablonunun başlanğıcı
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<content>\n  <custom_rules>\n'
    
    rule_count = 0
    for filename in os.listdir(RULES_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(RULES_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    rule_data = json.load(f)
                    
                    # JSON-dan dataları çəkirik
                    name = rule_data.get("qradar", {}).get("rule_name", "Bilinmeyen Rule")
                    desc = rule_data.get("description", "")
                    aql = rule_data.get("aql", "")
                    
                    # QRadar XML formatına salırıq
                    # Qeyd: AQL sorğusundakı SELECT hissəsini silib yalnız WHERE şərtini saxlamaq məsləhətdir
                    # Amma QRadar bəzi hallarda tam AQL qəbul edir.
                    rule_xml = f"""
    <custom_rule name="{name}" description="{desc}" type="EVENT" enabled="true">
      <rule_tests>
        <test type="AqlFilterTest">
           <aql_statement><![CDATA[{aql}]]></aql_statement>
        </test>
      </rule_tests>
    </custom_rule>"""
                    xml_content += rule_xml
                    rule_count += 1
                except Exception as e:
                    print(f"Xəta: {filename} oxunarkən problem oldu - {str(e)}")

    # XML sonluğu
    xml_content += '\n  </custom_rules>\n</content>'
    
    with open("custom_rules.xml", "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    print(f"Ümumi {rule_count} qayda custom_rules.xml faylına yazıldı.")

def create_manifest():
    print("Manifest faylı yaradılır...")
    manifest_content = """name=SOC_Automated_Rules
description=GitHub Actions vasitesile avtomatik deploy edilen SOC qaydalari
version=1.0
author=SOC_Team
guid=a1b2c3d4-e5f6-7890-abcd-ef1234567890"""
    
    with open("manifest.txt", "w", encoding="utf-8") as f:
        f.write(manifest_content)

def build_zip_extension():
    print("XML və Manifest ZIP formatında paketlənir...")
    with zipfile.ZipFile(ZIP_FILENAME, 'w') as zipf:
        zipf.write("custom_rules.xml")
        zipf.write("manifest.txt")
    print(f"{ZIP_FILENAME} yaradıldı.")

def deploy_to_qradar():
    print("QRadar API-yə yüklənir...")
    url = f"https://{QRADAR_HOST}/api/config/extension_management/extensions"
    headers = {
        "SEC": SEC_TOKEN,
        "Accept": "application/json"
    }
    
    with open(ZIP_FILENAME, 'rb') as f:
        files = {'extension': (ZIP_FILENAME, f, 'application/zip')}
        response = requests.post(url, headers=headers, files=files, verify=False)
        
    if response.status_code in [200, 201, 202]:
        print("✅ Bütün rule-lar QRadar-a uğurla göndərildi!")
        task_id = response.json().get('id')
        print(f"Extension Task ID: {task_id}. Yüklənmə prosesi QRadar arxa planında davam edir.")
    else:
        print(f"❌ Deploy zamanı xəta baş verdi: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    create_xml_from_json()
    create_manifest()
    build_zip_extension()
    deploy_to_qradar()
