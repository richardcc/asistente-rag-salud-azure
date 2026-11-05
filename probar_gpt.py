"""
Script para probar modelos GPT en Azure OpenAI desde la consola.
Uso: python probar_gpt.py [nombre_del_modelo_o_despliegue]
"""

import os
import sys
import json

def main():
    print("=" * 70)
    print("   PRUEBA DE MODELOS GPT EN AZURE OPENAI DESDE CONSOLA")
    print("=" * 70)

    # 1. Cargar configuracion local
    config_file = "config_rag.json"
    if not os.path.exists(config_file):
        print(f"[!] No se encontro el archivo '{config_file}'.")
        print("    Asegurate de haber ejecutado el despliegue previo o configurar las claves.")
        return

    with open(config_file, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    endpoint = cfg.get("AZURE_OPENAI_ENDPOINT")
    api_key = cfg.get("AZURE_OPENAI_KEY")

    if not endpoint or not api_key:
        print("[!] Falta AZURE_OPENAI_ENDPOINT o AZURE_OPENAI_KEY en config_rag.json.")
        return

    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version="2024-06-01"
    )

    # 2. Determinar que modelo probar
    modelo_objetivo = None
    if len(sys.argv) > 1:
        modelo_objetivo = sys.argv[1].strip()

    modelos_candidatos = [modelo_objetivo] if modelo_objetivo else ["gpt-4o-mini", "gpt-4o", "gpt-35-turbo", "gpt-4"]

    print(f"\n[i] Conectando al endpoint: {endpoint}")
    print("[i] Verificando despliegues disponibles de GPT...\n")

    despliegues_encontrados = []

    for mod in modelos_candidatos:
        print(f"Probando despliegue '{mod}'... ", end="", flush=True)
        try:
            resp = client.chat.completions.create(
                model=mod,
                messages=[
                    {"role": "system", "content": "Eres un asistente util."},
                    {"role": "user", "content": "Di 'HOLA GPT FUNCIONA' en una sola linea."}
                ],
                max_tokens=20,
                timeout=10
            )
            texto = resp.choices[0].message.content.strip()
            print(f"ACTIVO [OK]")
            print(f"   -> Respuesta: \"{texto}\"")
            despliegues_encontrados.append(mod)
        except Exception as e:
            err_str = str(e)
            if "DeploymentNotFound" in err_str or "404" in err_str:
                print("NO ENCONTRADO (no esta desplegado con este nombre)")
            elif "401" in err_str or "AccessDenied" in err_str:
                print("ERROR DE AUTENTICACION (revisa la API Key)")
                break
            else:
                print(f"ERROR: {err_str[:80]}...")

    print("\n" + "-" * 70)

    if despliegues_encontrados:
        modelo_activo = despliegues_encontrados[0]
        print(f"[V] Despliegue GPT operativo detectado: '{modelo_activo}'")
        print("-" * 70)

        # Prueba interactiva
        print("\nPuedes hacer una pregunta de prueba medica (ej: '¿Cuales son los rangos de IMC?'):")
        pregunta = input("\nTu pregunta (Enter para salir): ").strip()
        if pregunta:
            print("\nConsultando a GPT...")
            try:
                resp = client.chat.completions.create(
                    model=modelo_activo,
                    messages=[
                        {"role": "system", "content": "Eres un asistente de salud clinico y nutricional."},
                        {"role": "user", "content": pregunta}
                    ],
                    max_tokens=300,
                    temperature=0.3
                )
                print("\n" + "=" * 70)
                print(f"RESPUESTA DE {modelo_activo}:")
                print("=" * 70)
                print(resp.choices[0].message.content.strip())
                print("=" * 70)
            except Exception as e:
                print(f"[!] Error en la consulta: {e}")

        # Preguntar si desea actualizar config_rag.json
        if cfg.get("AZURE_OPENAI_CHAT_DEPLOYMENT") != modelo_activo:
            actualizar = input(f"\n¿Deseas configurar '{modelo_activo}' como el modelo principal de tu Web App? (S/n): ").strip().lower()
            if actualizar in ["", "s", "si", "y", "yes"]:
                cfg["AZURE_OPENAI_CHAT_DEPLOYMENT"] = modelo_activo
                with open(config_file, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=2)
                print(f"[V] Actualizado 'config_rag.json' con '{modelo_activo}'. Tu Web App ahora usara GPT.")

    else:
        print("[!] No se detecto ningun modelo GPT desplegado actualmente en este recurso.")
        print("\nCOMO DESPLEGAR 'gpt-4o-mini' EN AZURE EN 1 MINUTO:")
        print("  1. Entra a: https://oai.azure.com (Azure OpenAI Studio) o en portal.azure.com")
        print("  2. Selecciona tu recurso: 'openai-salud-0d1ff3'")
        print("  3. En el menu lateral, pulsa en 'Deployments' (Despliegues) -> 'Create deployment'")
        print("  4. Selecciona el modelo: 'gpt-4o-mini' (Version estandar)")
        print("  5. En 'Deployment name' escribe exactamente: gpt-4o-mini")
        print("  6. Pulsa 'Create' (Crear). En 30 segundos estara activo.")
        print("  7. Vuelve a ejecutar: python probar_gpt.py")

    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
