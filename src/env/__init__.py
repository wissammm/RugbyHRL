from gymnasium.envs.registration import register

register(
    id      = "RugbyHRLGame1-v0",
    entry_point = "src.env.env:Game1Env",
    max_episode_steps = 1_000,
)