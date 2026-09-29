from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.resources import Plate, TipRack

from praxis.backend.core.protocol_engine import protocol

# --- Pixel Art Definitions (8 rows x 5 columns) ---
# 1 = Fill, 0 = Empty
LETTERS = {
  "H": [
    [1, 1, 1, 1, 1, 1, 1, 1],  # Col 1
    [0, 0, 0, 1, 1, 0, 0, 0],  # Col 2
    [0, 0, 0, 1, 1, 0, 0, 0],  # Col 3
    [0, 0, 0, 1, 1, 0, 0, 0],  # Col 4
    [1, 1, 1, 1, 1, 1, 1, 1],  # Col 5
  ],
  "E": [
    [1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 1, 1, 0, 0, 1],
    [1, 0, 0, 1, 1, 0, 0, 1],
    [1, 0, 0, 1, 1, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
  ],
  "L": [
    [1, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 1],
  ],
  "O": [
    [0, 1, 1, 1, 1, 1, 1, 0],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [0, 1, 1, 1, 1, 1, 1, 0],
  ],
  "W": [
    [1, 1, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 1, 0],
    [1, 1, 1, 1, 1, 1, 0, 0],
  ],
  "R": [
    [1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 1, 0, 0, 0, 0],
    [1, 0, 0, 1, 1, 0, 0, 0],
    [1, 0, 0, 0, 1, 1, 0, 0],
    [0, 1, 1, 0, 0, 0, 1, 1],
  ],
  "D": [
    [1, 1, 1, 1, 1, 1, 1, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],
  ],
}


@protocol(
  name="Hello World Printer",
  description="Spells HELLO WORLD on 10 plates using liquid transfers",
)
async def hello_world(
  lh: LiquidHandler,
  tips: TipRack,
  trough: Plate,
  h_plate: Plate,
  e_plate: Plate,
  l1_plate: Plate,
  l2_plate: Plate,
  o1_plate: Plate,
  w_plate: Plate,
  o2_plate: Plate,
  r_plate: Plate,
  l3_plate: Plate,
  d_plate: Plate,
):
  """Spells HELLO WORLD by transferring liquid from a trough to 10 plates.
  """
  TEXT = "HELLOWORLD"

  # Collect plates for iteration
  plates = [
    h_plate,
    e_plate,
    l1_plate,
    l2_plate,
    o1_plate,
    w_plate,
    o2_plate,
    r_plate,
    l3_plate,
    d_plate,
  ]

  # Pick up tips once for the entire job (since we assume same liquid/dye)
  # Using an 8-channel range for the multichannel head
  await lh.pick_up_tips(tips["A1:H1"])

  try:
    # Loop through each character to print
    for letter_char, plate in zip(TEXT, plates, strict=False):
      print(f"Printing '{letter_char}' on {plate.name}...")

      pattern = LETTERS[letter_char]
      start_col = 4  # Center character on plate

      for col_idx, col_pattern in enumerate(pattern):
        # Calculate volumes: 50uL for pixels, 0 for empty space
        vols = [50.0 if bit else 0.0 for bit in col_pattern]

        if sum(vols) == 0:
          continue

        # Define source: Rows A-H of the trough's first column
        source_column = trough["A1":"H1"]

        # Define target: Rows A-H of the specific column on the plate
        target_col_num = start_col + col_idx
        target_column = plate[f"A{target_col_num}:H{target_col_num}"]

        # Perform the transfer using the 8-channel head
        # Since we picked up tips manually, this will use the currently attached tips
        await lh.transfer(source_column, target_column, vols=vols)

  finally:
    await lh.return_tips()
