def saludar_estudiante(nombre):
    return f"Bienvenido, {nombre}. Ya estás listo para construir proyectos en Python."


def calcular_total(sesiones, horas_por_sesion):
    return sesiones * horas_por_sesion


def calcular_progreso(completados, total):
    if total == 0:
        return 0
    return completados / total * 100


nombre_estudiante = "Tu nombre aquí"

print(saludar_estudiante(nombre_estudiante))
print("Horas del módulo:", calcular_total(2, 4))
print("Progreso:", calcular_progreso(3, 4), "%")
print("Progreso sin tareas:", calcular_progreso(0, 0), "%")
