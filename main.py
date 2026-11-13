"""Vehicle Performance Tracker: log trips, view MPG, and estimate trip costs."""
from dataclasses import dataclass

from drafter import (Button, Header, LineBreak, Page, SelectBox, Table,
                     TextBox, route, set_site_information, start_server)
from scipy import stats  # ADVANCED TECHNIQUE: not covered in class (see below)

set_site_information(
    author="YOUR NAME",
    description="Track vehicle trips, calculate MPG, and estimate trip costs.",
    sources=["Drafter documentation", "SciPy stats.linregress documentation"],
    planning=["planning.pdf"],
    links=["https://github.com/YOUR-USERNAME/YOUR-REPO"],
)

DEFAULT_GAS_PRICE = 3.50  # global constant (allowed)


@dataclass
class VehicleTrip:
    """One recorded trip: miles driven, gallons used, and price per gallon."""
    distance: float
    fuel_used: float
    gas_price: float


@dataclass
class State:
    """Data that persists across the whole website."""
    trips: list[VehicleTrip]
    current_gas_price: float
    target_distance: float
    prediction_result: float
    message: str


# ---------------------------------------------------------------- helpers
def parse_positive_number(text: str) -> float:
    """Convert text to a float; return -1.0 if invalid or not positive."""
    try:
        value = float(text)
    except ValueError:
        return -1.0
    if value <= 0:
        return -1.0
    return value


def calculate_mpg(distance: float, fuel_used: float) -> float:
    """Return miles per gallon, or 0.0 when no fuel was used."""
    if fuel_used > 0:  # prevents division by zero
        return distance / fuel_used
    return 0.0


def trip_cost(trip: VehicleTrip) -> float:
    """Return the dollar cost of fuel for one trip."""
    return trip.fuel_used * trip.gas_price


def average_mpg(trips: list[VehicleTrip]) -> float:
    """Return overall MPG: total miles divided by total gallons."""
    total_distance = 0.0
    total_fuel = 0.0
    for trip in trips:
        total_distance += trip.distance
        total_fuel += trip.fuel_used
    return calculate_mpg(total_distance, total_fuel)


def estimate_gallons(trips: list[VehicleTrip], distance: float) -> float:
    """Estimate gallons needed for a future trip.

    Fits a least-squares line through past (distance, fuel_used) pairs:
    slope = covariance / variance, intercept = mean_fuel - slope * mean_dist.
    Predicted gallons = slope * distance + intercept. If there are fewer
    than 2 trips, or every trip has the same distance, falls back to the
    average MPG instead.
    """
    count = len(trips)
    if count >= 2:
        mean_distance = sum(trip.distance for trip in trips) / count
        mean_fuel = sum(trip.fuel_used for trip in trips) / count
        spread = sum((trip.distance - mean_distance) ** 2 for trip in trips)
        if spread > 0:
            covariance = sum((trip.distance - mean_distance)
                             * (trip.fuel_used - mean_fuel) for trip in trips)
            slope = covariance / spread
            intercept = mean_fuel - slope * mean_distance
            predicted = slope * distance + intercept
            if predicted > 0:
                return predicted
    mpg = average_mpg(trips)
    if mpg > 0:
        return distance / mpg
    return 0.0




def trip_label(index: int) -> str:
    """Return the dropdown label for the trip at a 0-based index."""
    return f"Trip {index + 1}"


# ----------------------------------------------------------------- routes
@route
def index(state: State) -> Page:
    """Home dashboard with summary statistics and quick links."""
    content = [Header("Vehicle Performance Tracker"), state.message,
               LineBreak()]
    if len(state.trips) == 0:
        content.append("No trips logged yet. Log your first trip!")
    else:
        total_miles = sum(trip.distance for trip in state.trips)
        total_cost = sum(trip_cost(trip) for trip in state.trips)
        content.append(f"Trips logged: {len(state.trips)}")
        content.append(f"Total miles: {total_miles:.1f}")
        content.append(f"Average MPG: {average_mpg(state.trips):.2f}")
        content.append(f"Total fuel spending: ${total_cost:.2f}")
    content += [LineBreak(),
                Button("Log a Trip", log_trip_page),
                Button("View History", view_history_page),
                Button("Cost Calculator", cost_calculator_page)]
    return Page(state, content)


@route
def log_trip_page(state: State) -> Page:
    """Form page for entering a new trip."""
    return Page(state, [
        Header("Log New Trip"), state.message,
        "Distance (miles):", TextBox("distance_input", ""),
        "Fuel used (gallons):", TextBox("fuel_input", ""),
        "Gas price ($/gallon):",
        TextBox("gas_price_input", str(state.current_gas_price)),
        Button("Save Trip", add_trip),
        Button("Back", index),
    ])


@route
def add_trip(state: State, distance_input: str, fuel_input: str,
             gas_price_input: str) -> Page:
    """Validate form values and append a new VehicleTrip to the state."""
    distance = parse_positive_number(distance_input)
    fuel_used = parse_positive_number(fuel_input)
    gas_price = parse_positive_number(gas_price_input)
    if distance < 0 or fuel_used < 0 or gas_price < 0:
        state.message = "Please enter positive numbers in every box."
        return log_trip_page(state)
    state.trips.append(VehicleTrip(distance, fuel_used, gas_price))
    state.current_gas_price = gas_price
    state.message = (f"Saved! That trip got "
                     f"{calculate_mpg(distance, fuel_used):.2f} MPG.")
    return index(state)


@route
def view_history_page(state: State) -> Page:
    """Table of every recorded trip plus a selector for details."""
    content = [Header("Trip History")]
    if len(state.trips) == 0:
        content.append("No trips to show yet.")
    else:
        rows = [["Trip", "Miles", "Gallons", "MPG", "Cost"]]
        labels = []
        for position, trip in enumerate(state.trips):  # loop over instances
            labels.append(trip_label(position))
            rows.append([trip_label(position), f"{trip.distance:.1f}",
                         f"{trip.fuel_used:.2f}",
                         f"{calculate_mpg(trip.distance, trip.fuel_used):.2f}",
                         f"${trip_cost(trip):.2f}"])
        content += [Table(rows), "Choose a trip:",
                    SelectBox("selected_trip", labels, labels[0]),
                    Button("View Details", trip_details_page)]
    content.append(Button("Back", index))
    return Page(state, content)


@route
def trip_details_page(state: State, selected_trip: str) -> Page:
    """Detailed metrics for the trip chosen in the history page."""
    position = int(selected_trip.split(" ")[1]) - 1
    trip = state.trips[position]
    return Page(state, [
        Header(selected_trip),
        f"Distance: {trip.distance:.1f} miles",
        f"Fuel used: {trip.fuel_used:.2f} gallons",
        f"Gas price: ${trip.gas_price:.2f} per gallon",
        f"MPG: {calculate_mpg(trip.distance, trip.fuel_used):.2f}",
        f"Total cost: ${trip_cost(trip):.2f}",
        f"Cost per mile: ${trip_cost(trip) / trip.distance:.3f}",
        Button("Back to History", view_history_page),
    ])


@route
def cost_calculator_page(state: State) -> Page:
    """Form page for estimating the cost of an upcoming trip."""
    content = [Header("Trip Cost Calculator"), state.message]
    if len(state.trips) == 0:
        content.append("Log at least one trip first to unlock estimates.")
    else:
        content += ["Planned distance (miles):",
                    TextBox("target_input", str(state.target_distance)),
                    "Current gas price ($/gallon):",
                    TextBox("price_input", str(state.current_gas_price)),
                    Button("Estimate Cost", run_calculation)]
        if state.prediction_result > 0:
            content.append(f"Estimated cost: ${state.prediction_result:.2f}")
    content.append(Button("Back", index))
    return Page(state, content)


@route
def run_calculation(state: State, target_input: str,
                    price_input: str) -> Page:
    """Estimate the cost of a planned trip and store it in the state."""
    distance = parse_positive_number(target_input)
    price = parse_positive_number(price_input)
    if distance <= 0 or price <= 0:
        state.message = "Distance and gas price must be positive numbers."
        state.prediction_result = 0.0
        return cost_calculator_page(state)
    state.target_distance = distance
    state.current_gas_price = price
    gallons = estimate_gallons(state.trips, distance)
    state.prediction_result = gallons * price
    state.message = f"You'd need about {gallons:.2f} gallons."
    return cost_calculator_page(state)


if __name__ == "__main__":
    start_server(State([], DEFAULT_GAS_PRICE, 0.0, 0.0, ""))

