# PRD.md

# Sistema Inteligente de Gestión de Citas

## 1. Introducción

Este documento describe los requerimientos del sistema de gestión de citas diseñado para operar con un agente de inteligencia artificial capaz de interactuar con clientes y personal para consultar disponibilidad, agendar citas, modificar horarios y gestionar cancelaciones.

El sistema está diseñado para negocios como:

- Salones de belleza
- Clínicas
- Spas
- Barberías
- Consultorios

El objetivo es crear una infraestructura robusta que permita manejar:

- disponibilidad del personal
- múltiples servicios
- duración variable de servicios
- cambios de horario
- cancelaciones
- lista de espera
- notificaciones
- preferencias de clientes

El sistema será utilizado por un agente de IA que ejecutará herramientas (tools) para consultar la base de datos y tomar decisiones.

---

# 2. Objetivos del sistema

## Objetivo principal

Permitir gestionar citas de manera automática evitando conflictos de horario y ofreciendo siempre la mejor disponibilidad al cliente.

## Objetivos específicos

- Evitar doble agendamiento
- Validar duración de servicios
- Sugerir personal alternativo
- Permitir cambios de horario
- Gestionar cancelaciones
- Registrar historial de eventos
- Manejar operaciones masivas
- Soportar notificaciones

---

# 3. Tipos de usuarios

### Administrador

Puede:

- gestionar servicios
- gestionar personal
- ver agenda completa
- mover citas
- cancelar citas

### Staff

Puede:

- ver sus citas
- mover citas
- cancelar citas
- bloquear horarios

### Cliente

Puede:

- consultar servicios
- consultar precios
- agendar citas
- cancelar citas
- mover citas

---

# 4. Casos de uso principales

## Consulta de servicios

Ejemplo:

"¿Qué servicios ofrecen?"

El sistema debe consultar la tabla `services`.

---

## Consulta de precio

Ejemplo:

"¿Cuánto cuesta uñas en gel?"

El sistema debe consultar:

- services.name
- services.price

---

## Consulta de duración

Ejemplo:

"¿Cuánto tarda el servicio?"

Se calcula:

buffer_before + duration_minutes + buffer_after

---

## Consulta de disponibilidad

Ejemplo:

"¿Tiene Rosi espacio mañana?"

El sistema debe verificar:

- disponibilidad del staff
- citas existentes
- tiempo libre suficiente

---

## Crear cita

Flujo:

1. validar duración del servicio
2. verificar disponibilidad
3. verificar conflictos
4. crear cita

---

## Cancelar cita

Debe registrar:

- quién canceló
- motivo
- fecha

---

## Mover cita

Puede implicar:

- solicitud de cambio
- aceptación del cliente

---

## Cambios masivos

Ejemplo:

"Mover todas mis citas 30 minutos"

Debe registrarse como una operación masiva.

---

## Preferencias del cliente

El cliente puede:

- preferir cierto staff
- bloquear cierto staff

---

# 5. Reglas del sistema

## No superposición de citas

No puede existir una cita que cumpla:

new_start < existing_end

AND

new_end > existing_start

---

## Validación de duración

El servicio debe caber en el espacio libre.

Duración real:

buffer_before + duration_minutes + buffer_after

---

## Validación de disponibilidad

La cita debe estar dentro del horario definido en `staff_availability`.

---

## Validación de bloqueos

La cita no puede caer dentro de `staff_time_off`.

---

# 6. Funcionalidades para el agente de IA

El agente de IA debe tener herramientas para:

- consultar servicios
- consultar precios
- consultar disponibilidad
- crear cita
- cancelar cita
- mover cita
- sugerir staff alternativo

---

# DATA_BASE.md

# Base de Datos

Motor: PostgreSQL

---

# Entidades principales

- roles
- users
- staff_profiles
- client_profiles
- services
- appointments
- notifications
- waitlist

---

# Reglas de integridad

1. No se permiten citas superpuestas.
2. El servicio debe caber en el espacio disponible.
3. El staff debe ofrecer el servicio.

---

# Tablas

## roles

id (PK)
name
description
created_at

---

## users

id (PK)
role_id (FK)
name
email
phone
password_hash
status
email_verified
phone_verified
last_login
created_at
updated_at

---

## staff_profiles

id (PK)
user_id (FK)
specialty
bio
active
created_at

---

## client_profiles

id (PK)
user_id (FK)
notes
birthdate
created_at

---

## services

id (PK)
name
description
duration_minutes
buffer_before
buffer_after
price
active
created_at

---

## staff_services

id (PK)
staff_id
service_id

---

## staff_availability

id (PK)
staff_id
day_of_week
start_time
end_time
created_at

---

## staff_time_off

id (PK)
staff_id
start_datetime
end_datetime
reason
created_at

---

## appointments

id (PK)
client_id
staff_id
service_id
location_id
status
scheduled_start
scheduled_end
confirmation_deadline
confirmed_at
cancelled_by
cancel_reason
cancelled_at
rescheduled_from
created_by
notes
created_at
updated_at

---

## appointment_events

id
appointment_id
event_type
performed_by
old_start
old_end
new_start
new_end
reason
created_at

---

## appointment_change_requests

id
appointment_id
requested_by
old_start
old_end
proposed_start
proposed_end
reason
status
responded_at
created_at

---

## bulk_schedule_changes

id
staff_id
change_type
minutes_offset
reason
performed_by
created_at

---

## schedule_conflicts

id
appointment_id
conflict_type
detected_at
resolved
resolved_at

---

## reminder_rules

id
service_id
minutes_before
channel
active
created_at

---

## appointment_reminders

id
appointment_id
user_id
send_at
channel
status
response
sent_at
created_at

---

## waitlist

id
client_id
service_id
preferred_staff_id
preferred_start
preferred_end
status
created_at

---

## waitlist_notifications

id
waitlist_id
appointment_id
notified_at
expires_at
status

---

## notifications

id
user_id
type
related_entity_type
related_entity_id
message
status
sent_at
created_at

---

## appointment_files

id
appointment_id
uploaded_by
file_url
created_at

---

## payments

id
appointment_id
amount
currency
method
status
paid_at
created_at

---

# Índices recomendados

appointments (staff_id, scheduled_start, scheduled_end)

staff_services (service_id, staff_id)

staff_availability (staff_id, day_of_week)

staff_time_off (staff_id, start_datetime)

waitlist (service_id)

---

# Motor de disponibilidad

El sistema debe generar espacios disponibles considerando:

- duración del servicio
- citas existentes
- disponibilidad del staff
- bloqueos de agenda

Esto permitirá al agente de IA sugerir horarios automáticamente.

1. Arquitectura general del sistema

                    ┌────────────────────┐
                    │      CHAT / AI     │
                    │  (LLM + Tools)     │
                    └─────────┬──────────┘
                              │
                        Tool Layer
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                     APPLICATION LAYER                     │
│                        Use Cases                          │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                       DOMAIN LAYER                        │
│        Entities • Policies • Scheduling Engine            │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                   INFRASTRUCTURE LAYER                    │
│  Database • Repositories • Messaging • Notifications      │
└───────────────────────────────────────────────────────────┘

2. Estructura del proyecto

Usando Poetry para manejar dependencias.

project/
│
├── pyproject.toml
├── poetry.lock
├── .env
├── .env.example
├── README.md
│
├── src/
│   ├── domain
│   │   ├── entities
│   │   ├── value_objects
│   │   ├── repositories
│   │   ├── policies
│   │   └── scheduling_engine
│   │
│   ├── application
│   │   ├── use_cases
│   │   ├── services
│   │   └── dto
│   │
│   ├── infrastructure
│   │   ├── database
│   │   │   ├── models
│   │   │   ├── repositories
│   │   │   └── migrations
│   │   │
│   │   ├── notifications
│   │   ├── ai_tools
│   │   └── config
│   │
│   ├── interfaces
│   │   ├── api
│   │   └── chat_tools
│   │
│   └── main.py
│
└── tests
    ├── unit
    ├── integration
    └── e2e

3. Tecnologías recomendadas

Stack recomendado para este sistema.

Backend
Python 3.12+
FastAPI
Pydantic
Poetry
Base de datos

Principal:

PostgreSQL

ORM:

SQLAlchemy 2.0

Migraciones:

Alembic

Testing
pytest
pytest-mock
factory-boy
coverage


4. Configuración con .env

Nunca poner secretos en código.

Ejemplo .env:

APP_ENV=development

DATABASE_URL=postgresql://user:password@localhost:5432/appointments

5. Tools recomendadas para el agente de IA

El agente debe interactuar solo con tools, nunca con SQL.

get_services
get_service_details
get_service_price
get_service_duration

find_available_staff
find_available_slots

create_appointment
cancel_appointment
move_appointment

get_client_appointments

block_staff_time
unblock_staff_time

reschedule_day
cancel_day

add_waitlist
notify_waitlist

6. Tools específicas del chat

Ejemplo.

get_services

Permite responder:

"¿Qué servicios tienen?"

find_available_slots

Responde:

"¿Tienes espacio hoy?"

create_appointment

Responde:

"Agendame mañana a las 3"

move_appointment

Responde:

"No puedo ir mañana, muévela"

find_available_staff

Responde:

"Si Rosi no puede, ¿quién más?"


7. Flujo del agente

Usuario:

"Quiero uñas en gel mañana"

Agente ejecuta:

1 get_service
2 get_duration
3 find_available_staff
4 find_available_slots
5 create_appointment
8. Estrategia TDD

TDD debe iniciar desde el dominio.

Orden recomendado:

1. Scheduling engine

Test:

def test_no_overlap():
2. Policies

Test:

test_service_duration
3. Use cases

Test:

test_create_appointment
4. Repositories

Test:

test_save_appointment
5. Tools

Test:

test_chat_create_appointment
9. Estrategia de base de datos flexible

El dominio no depende de PostgreSQL.

Repositorios:

class AppointmentRepository(ABC):

Implementaciones:

PostgresAppointmentRepository
MongoAppointmentRepository
MemoryAppointmentRepository

Esto permite cambiar BD sin tocar dominio.

10. Seguridad

Recomendaciones críticas.

1. Nunca confiar en input del chat

Siempre validar con Pydantic.

2. Sanitizar datos

Evitar:

SQL injection
prompt injection
3. Control de acceso

Roles:

admin
staff
client

6. Logs auditables

Guardar eventos críticos:

citas creadas
cancelaciones
cambios masivos
11. Buenas prácticas
Domain first

Primero dominio, luego infraestructura.

Tools pequeñas

Una tool = una acción clara.

Idempotencia

Crear cita no debe duplicarse.

Event logging

Guardar cambios en:

appointment_events
Observabilidad

Registrar:

errores
latencia
uso del sistema

13. Arquitectura final
Chat AI
   │
Tools Layer
   │
Use Cases
   │
Scheduling Engine
   │
Repositories
   │
Database

14. Recomendación MUY importante

Tu sistema tendrá mucha lógica de agenda.

Te recomiendo separar completamente:

domain/scheduling_engine

porque ese módulo se vuelve el cerebro del sistema.

usa context7 para ver las mejores practicas actuales y find skills si necesitas algo más de contexto.

Recuerda crear la base de datos en postgres usando Docker para levantarel entorno de desarrollo 

