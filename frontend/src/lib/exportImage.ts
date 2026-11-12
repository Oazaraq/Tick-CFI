/** Export .jpg d'un SVG affiché : fond blanc (le JPEG n'a pas de transparence), rendu en 2x pour rester net,
 *  téléchargé par une URL d'objet (une URL data: trop longue donne un fichier illisible dans certains navigateurs). */
export async function exportJpeg(svg: SVGSVGElement, filename: string): Promise<void> {
  const xml = new XMLSerializer().serializeToString(svg)
  const img = new Image()
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve()
    img.onerror = () => reject(new Error('svg'))
    img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(xml)}`
  })
  const scale = 2
  const width = svg.width.baseVal.value
  const height = svg.height.baseVal.value
  const canvas = document.createElement('canvas')
  canvas.width = width * scale
  canvas.height = height * scale
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas')
  ctx.scale(scale, scale)
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, width, height)
  ctx.drawImage(img, 0, 0)
  const blob = await new Promise<Blob>((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error('jpeg'))), 'image/jpeg', 0.92))
  download(blob, filename)
}

/** Téléchargement d'un contenu généré dans le navigateur (image, CSV). */
export function download(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export const slug = (text: string) =>
  text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
