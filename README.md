# rl_bots
Bots for Rocket League using RLBot - AASMA Project @ IST 2021


# Project Structure
Within this repository are 3 different bots, **Primus**, **Capitão** and **NeuroRocket**. Each have a slightly different strucutre.

## Primus
Within Primus' folder, two sub folders can be found:
- **src** - Contains all of the bot's source code
- **training** - Contains training scenarios (used for testing and debugging the plays) made using RLBotTraining

The bot's main loop and implementation is written within the **src/bot.py** file. Within the utils folder, other modules developed for Primus can be found, such as the **src/utils/game_info** class, math/algebra functions within the **src/utils/math.py** and the intercept lookup tables and logic **src/intercept.py**.
The **src/plays** folder contains all of the individually developed plays (actions) that Primus can perform.

## Capitão
[TODO]

## NeuroRocket
[TODO]

# How to run
A Windows OS is required since Rocket League does not run on Linux systems

## Rocket League
- Download and install the [Epic Games Launcher](https://www.epicgames.com/store/en-US/) (top right corner where it says `Get Epic Games`)
- Create an account or Log in
- Install [Rocket League](https://www.epicgames.com/store/en-US/p/rocket-league)
- After installing Rocket League open it once so it makes all the changes to the registry that may be required

## RLBot
- Download this Github repository as a .zip file ([Link](https://github.com/HerouFenix/rl_bots/archive/refs/heads/main.zip))
- Extract it
- Download and install [RLBot](http://rlbot.org/) 
    - [Direct Link](https://github.com/RLBot/RLBotGUI/releases/download/v1.0/RLBotGUI.msi)
    - [Tutorial video](https://www.youtube.com/watch?v=oXkbizklI2U)
- Run the GUI
    - A desktop shortcut may have been created otherwise go to `%installation directory%/RLBotGUI/RLBotGUIX.exe`
- Add the bots to the RLBot Framework by adding the root folder of the .zip file that was extracted
    ![Add bots](./tutorial/add-bots.png)
- Install the required dependencies
    ![Install dependencies](./tutorial/install-deps.png)
    - rlgym
    - tensorflow
    - tmcp
    - numpy
    - If you think nothing is happening check the command-line opened by the RLBotGUI to see if there are any errors
- Drag the bots to the respective teams
![Drag bots](./tutorial/drag-bots.png)

- Set Epic Games as the preferred launcher
![Set launcher](./tutorial/set-launcher.png)

- Start the game! After a bit Rocket League should load with the bots in play and you in spectator mode!
![start match](./tutorial/start-match.png)
