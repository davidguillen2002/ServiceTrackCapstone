import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, RandomizedSearchCV, LeaveOneOut
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, precision_score, recall_score, confusion_matrix, balanced_accuracy_score
import joblib
import json
from collections import Counter


def cargar_datos(ruta_csv):
    """Carga los datos desde un archivo CSV."""
    return pd.read_csv(ruta_csv)


def preprocesar_datos(df):
    """Preprocesa los datos, selecciona las características relevantes y codifica las etiquetas."""
    features = [
        "nivel", "experiencia", "puntos", "calificacion_promedio",
        "servicios_completados", "incidentes_reportados", "tiempo_promedio_horas", "puntos_totales"
    ]
    target = "recomendacion_etiqueta"

    df = df.drop_duplicates()
    df = df.dropna(subset=features + [target])

    X = df[features]
    y = df[target]

    label_mapping = {label: idx for idx, label in enumerate(y.unique())}
    y = y.map(label_mapping)

    return X, y, label_mapping


def validar_distribucion_etiquetas(y):
    """Valida el balance de las etiquetas antes de entrenar."""
    etiqueta_counts = Counter(y)
    total = sum(etiqueta_counts.values())
    max_proporcion = max(etiqueta_counts.values()) / total
    if max_proporcion > 0.7:
        print("Advertencia: Las etiquetas están desbalanceadas. Considera ajustar los criterios de clasificación.")
    print(f"Distribución de etiquetas: {etiqueta_counts}")


def entrenar_modelo(X, y):
    """Entrena un modelo RandomForest optimizado y evalúa su desempeño."""
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [None, 10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4]
    }

    modelo_base = RandomForestClassifier(random_state=42, class_weight="balanced_subsample")

    if len(X) >= 20:
        cv = min(5, len(X) // 5)
        random_search = RandomizedSearchCV(
            estimator=modelo_base,
            param_distributions=param_grid,
            n_iter=50,
            cv=cv,
            scoring='f1_weighted',
            random_state=42,
            n_jobs=-1
        )
        random_search.fit(X, y)
        print(f"Mejores parámetros: {random_search.best_params_}")
        print(f"Mejor puntuación F1: {random_search.best_score_:.2f}")
        return random_search.best_estimator_
    else:
        print("Usando LeaveOneOut debido a la poca cantidad de datos...")
        loo = LeaveOneOut()
        for train_index, test_index in loo.split(X):
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]
            modelo_base.fit(X_train, y_train)
        print("Entrenamiento con LeaveOneOut completado.")
        return modelo_base


def evaluar_modelo(modelo, X, y):
    """Evalúa el modelo utilizando validación cruzada y métricas adicionales."""
    if len(X) >= 10:
        print("Validación cruzada...")
        scores = cross_val_score(modelo, X, y, cv=min(5, len(X) // 5), scoring="f1_weighted")
        print(f"Puntuación F1 promedio (validación cruzada): {scores.mean():.2f}")

    y_pred = modelo.predict(X)
    print("Evaluación del modelo:")
    print(f"Precisión: {precision_score(y, y_pred, average='weighted'):.2f}")
    print(f"Recall: {recall_score(y, y_pred, average='weighted'):.2f}")
    print(f"Balanced Accuracy: {balanced_accuracy_score(y, y_pred):.2f}")
    print(f"Reporte de clasificación:\n{classification_report(y, y_pred)}")
    print(f"Matriz de confusión:\n{confusion_matrix(y, y_pred)}")


def guardar_modelo(modelo, label_mapping, ruta_salida, ruta_mapping):
    """Guarda el modelo entrenado y el mapeo de etiquetas."""
    joblib.dump(modelo, ruta_salida)
    print(f"Modelo guardado en: {ruta_salida}")

    with open(ruta_mapping, "w") as f:
        json.dump(label_mapping, f)
    print(f"Mapeo de etiquetas guardado en: {ruta_mapping}")


if __name__ == "__main__":
    ruta_csv = "datos_tecnicos.csv"
    ruta_modelo = "modelo_recomendaciones.pkl"
    ruta_mapping = "label_mapping.json"

    print("Cargando datos...")
    df = cargar_datos(ruta_csv)
    print("Preprocesando datos...")
    X, y, label_mapping = preprocesar_datos(df)
    validar_distribucion_etiquetas(y)

    print("Entrenando modelo...")
    modelo = entrenar_modelo(X, y)

    print("Evaluando modelo...")
    evaluar_modelo(modelo, X, y)

    print("Guardando modelo...")
    guardar_modelo(modelo, label_mapping, ruta_modelo, ruta_mapping)