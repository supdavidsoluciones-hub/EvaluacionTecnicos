import requests

class APIClient:
    def __init__(self, base_url="http://127.0.0.1:5000/api/v1"):
        self.base_url = base_url
        self.token = None
        self.user_info = None

    def set_token(self, token: str):
        self.token = token

    def _headers(self):
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def login(self, username, password):
        url = f"{self.base_url}/auth/login"
        res = requests.post(url, json={"username": username, "password": password})
        if res.status_code == 200:
            data = res.json()
            self.token = data["access_token"]
            self.user_info = data["user_info"]
            return True, data
        else:
            try:
                err = res.json().get("detail", "Error al autenticar")
            except Exception:
                err = f"Error {res.status_code}"
            return False, err

    def get_dashboard_summary(self):
        url = f"{self.base_url}/dashboard/summary"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else {}

    def get_mobile_status(self):
        url = f"{self.base_url}/dashboard/mobile-status"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else []

    def get_alerts(self):
        url = f"{self.base_url}/dashboard/alerts"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else []

    def get_orders(self, mobile_id=None, order_date=None):
        url = f"{self.base_url}/orders"
        params = {}
        if mobile_id: params["mobile_id"] = mobile_id
        if order_date: params["order_date"] = order_date
        res = requests.get(url, headers=self._headers(), params=params)
        return res.json() if res.status_code == 200 else []

    def get_inspections(self, mobile_id=None):
        url = f"{self.base_url}/inspections"
        params = {}
        if mobile_id: params["mobile_id"] = mobile_id
        res = requests.get(url, headers=self._headers(), params=params)
        return res.json() if res.status_code == 200 else []

    def get_guarantees(self):
        url = f"{self.base_url}/guarantees/summary"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else {}

    def get_action_plans(self):
        url = f"{self.base_url}/action-plans"
        res = requests.get(url, headers=self._headers())
        return res.json() if res.status_code == 200 else []

    def export_excel(self, report_type="orders"):
        url = f"{self.base_url}/reports/export/excel?report_type={report_type}"
        res = requests.get(url, headers=self._headers())
        return res.content if res.status_code == 200 else None

    def export_pdf(self):
        url = f"{self.base_url}/reports/export/pdf"
        res = requests.get(url, headers=self._headers())
        return res.content if res.status_code == 200 else None
