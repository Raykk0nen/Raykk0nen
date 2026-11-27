'use strict'

const chart = [
  '..##........##.',
  '...#..T........',
  '.T...##...#....',
  '.....#....#....',
  '...#....T....#.',
  '.S...##.......P',
  '......#....T...',
  '..#......#.....',
  '.....T.#.......',
  '.##........##..',
]
const currents = [
  [[7, 3], [8, 3], [8, 4], [7, 4]],
  [[11, 7], [12, 7], [12, 8], [11, 8]],
]
const directions = { up: [0, -1], left: [-1, 0], down: [0, 1], right: [1, 0] }
const keys = { arrowup: 'up', w: 'up', arrowleft: 'left', a: 'left', arrowdown: 'down', s: 'down', arrowright: 'right', d: 'right' }
const tile = 24
const canvas = document.querySelector('#map')
const ctx = canvas.getContext('2d')
const action = document.querySelector('#start')
const reset = document.querySelector('#reset')
const message = document.querySelector('#message')
const gold = document.querySelector('#gold')
const hull = document.querySelector('#hull')
const directionButtons = [...document.querySelectorAll('[data-dir]')]
const treasures = chart.flatMap((row, y) => [...row].flatMap((symbol, x) => symbol === 'T' ? [`${x},${y}`] : []))
const spawn = chart.flatMap((row, y) => [...row].flatMap((symbol, x) => symbol === 'S' ? [[x, y]] : []))[0]

const sprites = {
  ship: [
    '.......gg.......', '.......ggggg....', '.......gg.......', '......wg........',
    '.....wwg.w......', '....wwwg.ww.....', '...wwwwg.www....', '..wwwwwg.wwww...',
    '.......g........', '.ggggggggggggggg', '..bbbbbbbbbbbbb.', '...bbbbbbbbbbb..',
    '....ddddddddd...', '..ttttttttttt...',
  ],
  coin: [
    '...ggg...', '..ggggg..', '.ggwwwgg.', 'ggwwggggg', 'ggwgggggg',
    'ggggggggg', '.gggggbb.', '..gggbb..', '...bbb...',
  ],
  reef: [
    '.......l......', '......lll.....', '......lsll....', '.....llssll...',
    '....lllsslll..', '....llssllssl.', '..lllsssllssll', '.lllssssllssss',
    'llsssssslddddd', '.dddddddddddd.', 'tt.t.ttttt.tt.',
  ],
  whirl: [
    '....ttt.....', '..tt...tt...', '.t...tt..t..', '.t..t..t..t.',
    't..t.tt.t..t', 't..t...t..t.', '.t..ttt..t..', '..tt...tt...', '....ttt.....',
  ],
  port: [
    '..t.........', '..tttt......', '..ttt.......', '..t.........', '..t.b.b.b.b.',
    'gggggggggggg', 'gbbgbbgbbgbg', 'gbbgbbgbbgbg', 'gggggggggggg', 'b.b......b.b',
  ],
}
const palette = { g: '#f7c979', w: '#fff1cf', b: '#a77447', d: '#243948', t: '#75dfde', l: '#9eaec3', s: '#576980' }

function sprite(name, x, y, mirror = false) {
  for (const [row, pixels] of sprites[name].entries()) {
    for (const [column, pixel] of [...pixels].entries()) {
      if (pixel === '.') continue
      ctx.fillStyle = palette[pixel]
      ctx.fillRect(x + (mirror ? pixels.length - column - 1 : column), y + row, 1, 1)
    }
  }
}

function sea() {
  ctx.fillStyle = '#103756'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  for (let i = 0; i < 270; i++) {
    const x = (i * 137 + 31) % canvas.width
    const y = (i * 59 + 9) % canvas.height
    ctx.fillStyle = i % 5 === 0 ? '#2c627a' : i % 3 === 0 ? '#194a67' : '#16415e'
    ctx.fillRect(x, y, 2 + (i % 5) * 2, 1)
  }
  ctx.fillStyle = '#214c66'
  for (let x = 0; x < canvas.width; x += tile) ctx.fillRect(x, 0, 1, canvas.height)
  for (let y = 0; y < canvas.height; y += tile) ctx.fillRect(0, y, canvas.width, 1)
}

function island(x, y) {
  ctx.fillStyle = '#17516a'
  ctx.fillRect(x + 2, y + 11, 21, 11)
  ctx.fillStyle = '#b78d55'
  ctx.fillRect(x + 4, y + 12, 17, 8)
  ctx.fillStyle = '#33796b'
  ctx.fillRect(x + 5, y + 8, 15, 8)
  ctx.fillStyle = '#519374'
  ctx.fillRect(x + 8, y + 6, 10, 5)
  sprite('reef', x + 5, y + 4)
}

let state

function draw() {
  sea()
  for (const [y, row] of chart.entries()) {
    for (const [x, cell] of [...row].entries()) {
      const left = x * tile
      const top = y * tile
      if (cell === '#') island(left, top)
      if (cell === 'T' && state.unclaimed.has(`${x},${y}`)) sprite('coin', left + 8, top + 8)
      if (cell === 'P') {
        ctx.fillStyle = '#215766'
        ctx.fillRect(left + 1, top + 1, 22, 22)
        sprite('port', left + 7, top + 7)
      }
      if (cell === 'S') {
        ctx.fillStyle = '#347783'
        ctx.fillRect(left + 3, top + 21, 18, 1)
      }
    }
  }
  for (const track of currents) {
    const [x, y] = track[state.turn % track.length]
    sprite('whirl', x * tile + 6, y * tile + 7)
  }
  ctx.fillStyle = '#123b56'
  ctx.fillRect(state.x * tile + 3, state.y * tile + 4, 19, 17)
  sprite('ship', state.x * tile + 4, state.y * tile + 5, state.west)
  gold.value = `${treasures.length - state.unclaimed.size} / ${treasures.length}`
  hull.value = `${state.hull} / 3`
  canvas.setAttribute('aria-label', `Mapa de Maré de Ouro. Navio na coluna ${state.x + 1}, linha ${state.y + 1}. Porto na última coluna, linha 6.`)
}

function begin(playing) {
  state = { x: spawn[0], y: spawn[1], turn: 0, west: false, hull: 3, unclaimed: new Set(treasures), playing }
  message.textContent = playing ? 'Navio em movimento. Os redemoinhos mudam de posição a cada manobra.' : 'Você está no ancoradouro. Tudo pronto para zarpar?'
  action.hidden = playing
  reset.hidden = !playing
  directionButtons.forEach(button => { button.disabled = !playing })
  draw()
  if (playing) directionButtons[3].focus({ preventScroll: true })
}

function finish(won) {
  state.playing = false
  message.textContent = won ? 'Porto alcançado! Os 5 tesouros chegaram com você.' : 'O casco cedeu. Recomece a travessia.'
  directionButtons.forEach(button => { button.disabled = true })
  action.textContent = 'Jogar de novo'
  action.hidden = false
  reset.hidden = true
  action.focus({ preventScroll: true })
}

function sail(direction) {
  if (!state.playing) return
  const [dx, dy] = directions[direction]
  const x = state.x + dx
  const y = state.y + dy
  const cell = chart[y]?.[x]
  if (!cell) {
    message.textContent = 'Limite da carta. Mude de direção.'
    return
  }
  state.turn++
  if (dx !== 0) state.west = dx < 0
  if (cell !== '#') {
    state.x = x
    state.y = y
  }

  const whirlpool = currents.some(track => {
    const [cx, cy] = track[state.turn % track.length]
    return cx === state.x && cy === state.y
  })
  const treasure = state.unclaimed.delete(`${state.x},${state.y}`)
  if (cell === '#' || whirlpool) {
    state.hull--
    message.textContent = cell === '#' ? 'O navio bateu no recife. Você perdeu 1 ponto de casco.' : 'Um redemoinho atingiu o navio. Você perdeu 1 ponto de casco.'
  } else if (treasure) {
    message.textContent = state.unclaimed.size ? `Tesouro a bordo. Faltam ${state.unclaimed.size}.` : 'Todos os tesouros a bordo. Rumo ao porto!'
  } else if (cell === 'P' && state.unclaimed.size) {
    message.textContent = `Porto à vista. Ainda faltam ${state.unclaimed.size} tesouros.`
  } else {
    message.textContent = 'Navegando pela carta.'
  }

  if (state.hull === 0) finish(false)
  else if (cell === 'P' && !state.unclaimed.size) finish(true)
  draw()
}

action.addEventListener('click', () => begin(true))
reset.addEventListener('click', () => begin(true))
directionButtons.forEach(button => button.addEventListener('click', () => sail(button.dataset.dir)))
document.addEventListener('keydown', event => {
  const direction = keys[event.key.toLowerCase()]
  if (!direction || !state.playing || event.ctrlKey || event.altKey || event.metaKey) return
  event.preventDefault()
  if (!event.repeat) sail(direction)
})
begin(false)
