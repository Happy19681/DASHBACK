"""Storage rules for CRUD-backed dashboard sections."""


def field(kind: str, required: bool = False, options: tuple[str, ...] = ()) -> dict:
    return {"type": kind, "required": required, "options": options}


PAGE_RESOURCES = {
    "products": {
        "name": field("text", True), "category": field("text", True),
        "price": field("number", True), "stock": field("integer", True),
        "status": field("select", True, ("Active", "Draft", "Archived")),
    },
    "reports": {
        "title": field("text", True), "period": field("select", True, ("Daily", "Weekly", "Monthly", "Yearly")),
        "description": field("textarea"), "status": field("select", True, ("Saved", "Draft")),
    },
    "messages": {
        "subject": field("text", True), "recipient": field("text", True),
        "message": field("textarea", True), "status": field("select", True, ("Unread", "Read", "Archived")),
    },
    "team-performance": {
        "name": field("text", True), "role": field("text", True),
        "sales": field("number", True), "target": field("number", True),
        "status": field("select", True, ("Active", "Inactive")),
    },
    "campaigns": {
        "name": field("text", True), "channel": field("text", True),
        "budget": field("number", True), "startDate": field("date", True),
        "endDate": field("date", True), "status": field("select", True, ("Draft", "Active", "Completed")),
    },
    "customers": {
        "name": field("text", True), "email": field("email", True),
        "phone": field("text"), "status": field("select", True, ("Active", "Inactive")),
        "notes": field("textarea"),
    },
    "channels": {
        "name": field("text", True), "type": field("text", True),
        "url": field("url"), "status": field("select", True, ("Connected", "Paused", "Disconnected")),
    },
    "orders": {
        "orderNumber": field("text", True), "customer": field("text", True),
        "product": field("text", True), "quantity": field("integer", True),
        "amount": field("number", True), "status": field("select", True, ("Pending", "Processing", "Completed", "Cancelled")),
        "date": field("date", True),
    },
    "roles": {
        "name": field("text", True), "description": field("textarea"),
        "permissions": field("textarea", True), "status": field("select", True, ("Active", "Inactive")),
    },
    "billing": {
        "plan": field("text", True), "amount": field("number", True),
        "billingCycle": field("select", True, ("Monthly", "Annual")),
        "status": field("select", True, ("Active", "Past due", "Cancelled")),
        "nextBillingDate": field("date", True),
    },
    "integrations": {
        "name": field("text", True), "provider": field("text", True),
        "details": field("textarea"), "status": field("select", True, ("Connected", "Disconnected")),
    },
    "support": {
        "subject": field("text", True), "customer": field("text", True),
        "priority": field("select", True, ("Low", "Medium", "High")),
        "status": field("select", True, ("Open", "In Progress", "Resolved")),
        "description": field("textarea"),
    },
    "help-center": {
        "title": field("text", True), "category": field("text", True),
        "content": field("textarea", True), "status": field("select", True, ("Draft", "Published")),
    },
    "settings": {
        "key": field("text", True), "value": field("textarea", True),
        "description": field("textarea"),
    },
}
