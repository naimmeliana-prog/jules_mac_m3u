# jules_mac_m3u

Herramienta para convertir un portal MAC Stalker a una URL M3U auto-actualizable con categorías.

Esta herramienta está diseñada para ejecutarse automáticamente mediante GitHub Actions y generar un archivo `lista_iptv.m3u` en este repositorio, el cual puedes usar directamente en cualquier reproductor IPTV proporcionando la URL en crudo (Raw).

## Características

- Filtrado de Live TV, VOD y Series por idioma: estrictamente Español (ES).
- Carga de metadatos completos para Películas y Series (Sinopsis, Año, Director, Reparto, Póster/Logo).
- Generación y extracción correcta de temporadas y episodios de Series.
- Integración explícita con el reproductor WebOS (evita que las películas se crucen a la sección de TV en Vivo añadiendo `dummy=/movie/video.mp4`).
- Auto-actualizable y gratuita: Utiliza GitHub Actions para ejecutarse cada noche y subir los cambios a este repositorio.

## Cómo usar el link M3U auto-actualizable

Copia el enlace a la versión "Raw" del archivo `lista_iptv.m3u` una vez que GitHub Actions genere la lista. El enlace debería verse de esta forma:
`https://raw.githubusercontent.com/naimmeliana-prog/jules_mac_m3u/main/lista_iptv.m3u`
