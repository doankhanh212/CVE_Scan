from kev_db import init_db
from kev_client import update_db_from_kev
from cvss_mapper import inject_e_metric

init_db()
update_db_from_kev()

base_vector = "CVSS:4.0/AV:N/AC:L/AT:N/PR:N/UI:N/VC:H/VI:H/VA:H"
cve = "CVE-2023-12345"

print(inject_e_metric(base_vector, cve))
