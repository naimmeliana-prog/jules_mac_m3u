# jules_mac_m3u

Herramienta para convertir un portal MAC Stalker a una URL M3U auto-actualizable con categorías.

Esta herramienta está diseñada para ejecutarse automáticamente mediante GitHub Actions y generar un archivo `lista_iptv.m3u` en este repositorio, el cual puedes usar directamente en cualquier reproductor IPTV proporcionando la URL en crudo (Raw).

## Características

- Filtrado de Live TV por idiomas: Español (ES), Francés (FR) e Inglés (UK/EN).
- Filtrado de VOD y Series por idiomas: Español (ES) y Francés (FR).
- Carga de metadatos completos para Películas y Series (Sinopsis, Año, Director, Reparto, Póster/Logo).
- Generación y extracción correcta de temporadas y episodios de Series utilizando el formato de token Base64 de portales MAC Stalker.
- Auto-actualizable y gratuita: Utiliza GitHub Actions para ejecutarse cada noche y subir los cambios a este repositorio.

## Cómo usar el link M3U auto-actualizable

Copia el enlace a la versión "Raw" del archivo `lista_iptv.m3u` una vez que GitHub Actions genere la lista. El enlace debería verse de esta forma:
`https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/lista_iptv.m3u`
