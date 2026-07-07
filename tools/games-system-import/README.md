# Games System

A standalone collection of web-based multiplayer games for project integration and secondary development.

## Games

| Game | Path | Status |
|------|------|--------|
| 大乱斗 Arena Brawl | [`games/arena-brawl`](games/arena-brawl) | Active |
| 敲冰块大逃脱 Ice Climber Arena | [`games/ice-climber-arena`](games/ice-climber-arena) | Active |
| 炸弹派对 Bomb Party | [`games/bomb-party`](games/bomb-party) | Active |
| 疯狂碰碰车 Crazy Bumper Cars | [`games/crazy-bumper-cars`](games/crazy-bumper-cars) | Active |
| 3D射击游戏 Neon Arena FPS | [`games/neon-arena-fps`](games/neon-arena-fps) | Active |

## Getting Started

Each game is self-contained in its own directory under `games/`. See the game's own `README.md` for setup and run instructions.

```bash
# Install dependencies for all games
npm install

# Run a specific game
cd games/arena-brawl
npm start
```

## Adding a New Game

1. Create a new directory under `games/<your-game>/`
2. Add the game's `package.json`, source code, and `README.md`
3. Update the table above
4. Commit and push

## License

[MIT](LICENSE)
