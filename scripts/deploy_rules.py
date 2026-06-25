import os
import json
import zipfile
import requests
import urllib3
import sys

# SSL xəbərdarlıqlarını söndürürük
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Dəyişənləri mühitdən alırıq və URL-i təmizləyirik
QRADAR_HOST = os.environ.get("QRADAR_HOST")
SEC_TOKEN = os.environ.get("QRADAR_SEC_TOKEN")
if QRADAR_HOST and QRADAR_HOST.startswith("http"):
    QRADAR_HOST = QRADAR_HOST.split("://")[-1]

RULES_DIR = "rules/"
ZIP_FILENAME = "soc_rules_extension.zip"

def create_xml_from_json():
    print("JSON faylları oxunur və XML formatına çevrilir...")
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n<content>\n  <custom_rules>\n'
    rule_count = 0
    
    for filename in os.listdir(RULES_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(RULES_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                try:
                    rule_data = json.load(f)
                    name = rule_data.get("qradar", {}).get("rule_name", "Bilinmeyen Rule")
                    desc = rule_data.get("description", "")
                    # Burada AQL-in yalnız şərt hissəsi qalmalıdır
                    aql = rule_data.get("aql", "")
                    
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
                    print(f"❌ Xəta: {filename} oxunarkən problem oldu - {str(e)}")

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
    print(f"{ZIP_FILENAME} uğurla yaradıldı.")

def deploy_to_qradar():
    print("QRadar API-yə yüklənir...")
    upload_url = f"https://{QRADAR_HOST}/api/config/extension_management/extensions"
    headers = {
        "SEC": SEC_TOKEN,
        "Accept": "application/json"
    }
    
    with open(ZIP_FILENAME, 'rb') as f:
        # DİQQƏT: Parametr adı "extension" yox, "file" olaraq dəyişdirildi
        files = {'file': (ZIP_FILENAME, f, 'application/zip')}
        response = requests.post(upload_url, headers=headers, files=files, verify=False)
        
    if response.status_code in [200, 201, 202]:
        ext_data = response.json()
        ext_id = ext_data.get('id')
        print(f"✅ Bütün rule-lar QRadar-a uğurla GÖNDƏRİLDİ! Extension ID: {ext_id}")
        
        # --- AVTOMATİK QURAŞDIRMA MƏRHƏLƏSİ ---
        print("Avtomatik Install prosesi başladılır...")
        install_url = f"https://{QRADAR_HOST}/api/config/extension_management/extensions/{ext_id}/install"
        install_resp = requests.post(install_url, headers=headers, verify=False)
        
        if install_resp.status_code in [200, 201, 202]:
            print("✅ Qaydalar sistemə tam QURAŞDIRILDI! Artıq Offenses -> Rules bölməsindədir.")
        else:
            print(f"❌ Install zamanı xəta: HTTP {install_resp.status_code}")
            print(install_resp.text)
            sys.exit(1) # Action-u Failed vəziyyətinə salır
    else:
        print(f"❌ Yükləmə (Deploy) zamanı xəta baş verdi: HTTP {response.status_code}")
        print(response.text)
        sys.exit(1) # Action-u Failed vəziyyətinə salır

if __name__ == "__main__":
    create_xml_from_json()
    create_manifest()
    build_zip_extension()
    deploy_to_qradar()
