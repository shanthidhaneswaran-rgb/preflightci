
from src.service_detector import detect_service_references

results = detect_service_references(
    "tests/sample_banking_services.py"
)

for result in results:
    print(
        "{} {} | host={} | line={}".format(
            result["method"],
            result["url"],
            result["host"],
            result["line"],
        )
    )

print("Total references:", len(results))
