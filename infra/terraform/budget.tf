# AWS Budgets - Monthly cost guard for QuickDCP (fixed)
# Self-contained: declares its own variables for portability.

variable "project" {
  description = "Project name for tagging/budget name"
  type        = string
  default     = "quickdcp"
}

variable "budget_usd" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 150
}

variable "alert_emails" {
  description = "List of email addresses to receive budget alerts"
  type        = list(string)
  default     = ["ops@quickdcp.com"]
}

resource "aws_budgets_budget" "monthly" {
  name         = "${var.project}-monthly"
  budget_type  = "COST"
  limit_amount = format("%.2f", var.budget_usd) # provider expects string
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Actual spend crosses 80%, 100%, 120%
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alert_emails
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 120
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.alert_emails
  }

  # Forecasted spend exceeds 100%
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.alert_emails
  }
}
