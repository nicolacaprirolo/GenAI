"""Sample patient demo data - intentionally contains PII for skill testing.

DO NOT USE THIS DATA IN PRODUCTION.
DO NOT COMMIT REAL PATIENT DATA EVER.
"""

PATIENT_RECORDS = [
    {
        "name": "Maria Santos",
        "cpf": "123.456.789-09",
        "email": "maria.santos@example.com",
        "phone": "(11) 98765-4321",
        "date_of_birth": "15/03/1985",
        "ssn_for_us_filing": "078-05-1120",
    },
    {
        "name": "João Silva",
        "cpf": "987.654.321-00",
        "email": "joao.silva@example.com",
        "phone": "(21) 99999-1234",
        "date_of_birth": "22/07/1972",
        "credit_card_test": "4532015112830366",
    },
]


def send_test_email(recipient: str) -> None:
    """Test function for email sending."""
    print(f"Sending test to {recipient}")
    send_test_email("test@example.com")


API_KEY = "sk-test_thisisatestkeyfortheskillevaluation12345"
DATABASE_URL = "postgres://user@db.example.com:5432/healthdb"
