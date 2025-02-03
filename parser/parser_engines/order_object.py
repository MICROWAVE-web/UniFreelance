import json
from typing import List


class Order:
    def __init__(self, task_id: str, title: str, payment: str, description: str,
                 direct_url: str, additional_files: List[str] = None, platform: str = None, ):
        if additional_files is None:
            additional_files = []
        self._task_id = str(task_id)
        self._title = str(title)
        self._payment = payment.replace("\n", " ")
        self._description = str(description)
        self._direct_url = str(direct_url)
        self._additional_files = additional_files
        self._platform = platform

    # Getters
    @property
    def task_id(self):
        return self._task_id

    @property
    def title(self):
        return self._title

    @property
    def payment(self):
        return self._payment

    @property
    def description(self):
        return self._description

    @property
    def direct_url(self):
        return self._direct_url

    @property
    def additional_files(self):
        return [str(_file_url) for _file_url in self._additional_files]

    @property
    def platform(self):
        return self._platform

    # Method to print order details
    def print_order(self):
        print("Order Details:")
        print(f"Task ID: {self.task_id}")
        print(f"Title: {self.title}")
        print(f"Payment: {self.payment}")
        print(f"Description: {self.description}")
        print(f"Direct URL: {self.direct_url}")
        print(f"Additional Files: {self._additional_files}")
        print(f"Platform: {self._platform}")
        print()

    def __str__(self):
        return f"""Order Details:
Task ID: {self.task_id}
Title: {self.title}
Payment: {self.payment}
Description: {self.description}
Direct URL: {self.direct_url}
Additional Files: {self._additional_files}
Platform: {self._platform}
"""

    def __repr__(self):
        return f"<Order(id={self.task_id}, title={self.title}, payment={self.payment}, platform={self._platform})>"

    def to_dict(self):
        return {
            'task_id': self.task_id,
            'title': self.title,
            'payment': self.payment,
            'description': self.description,
            'direct_url': self.direct_url,
            'additional_files': self.additional_files,
            'platform': self.platform,
        }

    def toJSON(self):
        return json.dumps(
            self,
            default=lambda o: o.__dict__,
            sort_keys=True,
            indent=4)


if __name__ == "__main__":
    me = Order(
        task_id="123",
        title="My Order",
        payment="123.456",
        description="My Order",
        direct_url="https://example.com",
        additional_files=["file.txt"]
    )

    print(me.toJSON())
