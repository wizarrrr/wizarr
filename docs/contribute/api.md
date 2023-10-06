# Wizarr API
Wizarr API

## Version: 1.0

---
## Accounts
Accounts related operations

### /accounts/

#### POST
##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

#### GET
##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

### /accounts/{username}

#### GET
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| username | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

#### PUT
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| username | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

---
## Authentication
Authentication related operations

### /auth/login

#### POST
##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

### /auth/logout

#### POST
##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

---
## Notifications
Notifications related operations

### /notifications/

#### POST
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| payload | body |  | Yes | [NotificationsPostModel](#notificationspostmodel) |

##### Responses

| Code | Description |
| ---- | ----------- |
| 201 | Notification created successfully |
| 400 | Invalid notification agent |
| 409 | Notification agent already exists |
| 500 | Internal server error |

#### GET
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| X-Fields | header | An optional fields mask | No | string (mask) |

##### Responses

| Code | Description | Schema |
| ---- | ----------- | ------ |
| 200 | Success | [ [NotificationsGetModel](#notificationsgetmodel) ] |

### /notifications/{notification_id}

#### GET
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| notification_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

#### DELETE
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| notification_id | path |  | Yes | integer |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

---
## Settings
Settings related operations

### /settings/

#### POST
##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

#### GET
##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

### /settings/{setting_id}

#### GET
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| setting_id | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

#### PUT
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| setting_id | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

#### DELETE
##### Parameters

| Name | Located in | Description | Required | Schema |
| ---- | ---------- | ----------- | -------- | ------ |
| setting_id | path |  | Yes | string |

##### Responses

| Code | Description |
| ---- | ----------- |
| 200 | Success |

---
### Models

#### NotificationsPostModel

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| name | string | The name of the notification | Yes |
| type | string | The type of the notification | Yes |
| url | string | The URL of the notification | Yes |
| username | string | The username of the notification | No |
| password | string | The password of the notification | No |

#### NotificationsGetModel

| Name | Type | Description | Required |
| ---- | ---- | ----------- | -------- |
| id | integer | The ID of the notification | Yes |
| name | string | The name of the notification | Yes |
| type | string | The type of the notification | Yes |
| url | string | The URL of the notification | Yes |
| username | string | The username of the notification | No |
| password | string | The password of the notification | No |
| created | dateTime | The date the notification was created | Yes |
