# Plataforma web inteligente para adopción y reconocimiento facial de mascotas

El presente Proyecto es como parte de un proyecto de tesis una plataforma web inteligente desarrollada, con el objetivo de integrar módulos de **adopción responsable** y **reconocimiento facial de mascotas**, representando una solución innovadora, viable y socialmente relevante en Ecuador.

Este sistema está construido utilizando tecnologías como **Django**, **PostgreSQL** y **OpenCV**, permitiendo:

- La gestión segura de la información de animales.
- El emparejamiento eficiente entre mascotas y adoptantes.
- La creación de una base de datos de animales extraviados.
- El uso de algoritmos de visión computacional para identificar mascotas a partir de fotografías.

Con ello, esta plataforma busca no solo dar respuesta a una necesidad técnica, sino también contribuir a reducir el abandono animal y fomentar una cultura de tenencia responsable.

---

## Objetivos del proyecto

- Desarrollar una plataforma web integral para facilitar la adopción responsable de mascotas.
- Implementar un sistema de reconocimiento facial animal que permita localizar animales extraviados.
- Promover una solución sostenible y escalable que fortalezca los procesos de adopción en Ecuador.

---

## Tecnologías utilizadas

- 🐍 Python 3.x
- 🌐 Django 4.x
- 🐘 PostgreSQL
- 🧠 OpenCV (Visión computacional)
- 🛠️ HTML5, CSS3, Bootstrap

---

## Requisitos previos

- Python ≥ 3.8
- PostgreSQL
- Git
- pip y virtualenv

---

## Arquitectura

<img width="1208" height="643" alt="Arquitectura" src="https://github.com/user-attachments/assets/0ad62525-5482-4022-95d6-aa41b1fe44d2" />


## Instalación del entorno de desarrollo

1. **Clona el repositorio**

```bash
git clone https://github.com/Miguetorresp/tesis.git
cd tesis
```

2. Crea y activa un entorno virtual

```bash
python -m venv env
# Windows
env\Scripts\activate
# macOS/Linux
source env/bin/activate
```

3. Instala las dependencias

```bash
pip install -r requirements.txt
```

4. Configura PostgreSQL

```bash
-- En consola psql
CREATE DATABASE petface_db;
CREATE USER petface_user WITH PASSWORD 'clave_segura';
GRANT ALL PRIVILEGES ON DATABASE petface_db TO petface_user;

```

5. Configura PostgreSQL

```bash
DEBUG=True
SECRET_KEY=tu_clave_secreta_django
DB_NAME=petface_db
DB_USER=petface_user
DB_PASSWORD=clave_segura
DB_HOST=localhost
DB_PORT=5432
```

6. Ejecuta migraciones y crea el superusuario

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

7. Inicia el servidor de desarrollo

```bash
python manage.py runserver
```
