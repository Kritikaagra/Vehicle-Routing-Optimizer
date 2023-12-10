from flask import Flask, render_template, request
import pandas as pd
from ortools.sat.python import cp_model as pywrapcp
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp


app = Flask(__name__)

def get_location_name(index, origin, destinations):
    if index == 0:
        return origin
    return destinations[index - 1]

def solve_vehicle_routing(data):
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                            data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

    routing.AddDimensionWithVehicleCapacity(
                demand_callback_index,
                    0,  # null capacity slack
                    data['vehicle_capacities'],  # vehicle maximum capacities
                    True,  # start cumul to zero
                    'Capacity'
                )

    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        routing.AddConstantDimensionWithSlack(
                        0,  # additional slack
                        data['initial_inventory'],  # initial inventory at the depot
                        data['initial_inventory'],  # maximum inventory at the depot
                        True,  # start cumul to zero
                        'Inventory'
                    )

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.time_limit.seconds = 1

    # Solve the routing problem
    solution = routing.SolveWithParameters(pywrapcp.DefaultRoutingSearchParameters())

    if solution:
        routes = []

        for vehicle_id in range(data['num_vehicles']):
            index = routing.Start(vehicle_id)
            route_distance = 0
            route_load = 0
            route_locations = []

            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                route_load += data['demands'][node_index]
                route_locations.append(node_index)
                previous_index = index
                index = solution.Value(routing.NextVar(index))
                route_distance += routing.GetArcCostForVehicle(previous_index, index, vehicle_id)

            route_locations_names = [get_location_name(i, data['origin'], data['destinations']) for i in route_locations]

            routes.append({'distance': route_distance, 'load': route_load, 'locations': route_locations_names})

        return routes

    return []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch', methods=['POST'])
def main_fetch():
    origin_df = pd.read_csv("C:\\Users\\harsh\\Downloads\\locations & cordinates - shipment.csv")
    capacity_df = pd.read_csv("C:\\Users\\harsh\\Downloads\\locations & cordinates - Orgin_Capacity.csv")
    origin_dict = dict(zip(origin_df['Destination'], origin_df['Origin']))
    capacity_dict = dict(zip(capacity_df['Origin'], capacity_df['capacity']))

    number_of_locations = int(request.form['demand-input'])

    results = []

    for i in range(number_of_locations):
        name_key = f'location_name_{i + 1}'
        demand_key = f'location_demand_{i + 1}'
        destination_name = request.form[name_key]
        destination_demand = int(request.form[demand_key])

        origin_name = origin_dict[destination_name]
        origin_capacity = capacity_dict[origin_name]

        result_item = {
            'origin': origin_name,
            'capacity': origin_capacity,
            'destinations': [(destination_name, destination_demand)]
        }

        for result in results:
            if result['origin'] == origin_name:
                result['destinations'].append((destination_name, destination_demand))
                break
        else:
            results.append(result_item)

    routes = []
    re = []

    for result_item in results:
        data = {
            'origin': result_item['origin'],
            'origin_capacity' : result_item['capacity'],
            'destinations': [dest for dest, _ in result_item['destinations']],
            'demands': [0] + [demand for _, demand in result_item['destinations']],
            'num_vehicles': 5,
            'vehicle_capacities': [1000,1000,1000,1000,1000],
            'depot': 0,
            'initial_inventory': 1500,
            # Add distance matrix setup here based on your data
        }
        dem_sum = sum(data['demands'])
        if data['origin_capacity'] >= dem_sum:
            
            df = pd.read_csv("C:\\Users\\harsh\\Downloads\\locations & cordinates - distance2 (2).csv", index_col=0)
            distance_matrix = []
            a = [0]
            for dest in data['destinations']:
                a.append(df.loc[data['origin'], dest])
            distance_matrix.append(a)

            for dest1 in data['destinations']:
                b = [df.loc[data['origin'], dest1]]
                for dest2 in data['destinations']:
                    b.append(df.loc[dest1, dest2])
                distance_matrix.append(b)

            data['distance_matrix'] = distance_matrix

            result_for_item = solve_vehicle_routing(data)
            routes.append(result_for_item)
        else:
            
            orgn = data['origin']
            
                
            if len(data['destinations']) == 1:
                re.append([orgn,data['destinations'][0]])
            if len(data['destinations']) == 2:
                re.append([orgn,data['destinations'][0],data['destinations'][1]])
            if len(data['destinations']) == 3:
                re.append([orgn,data['destinations'][0],data['destinations'][1],data['destinations'][2]])
            if len(data['destinations']) == 4:
                re.append([orgn,data['destinations'][0],data['destinations'][1],data['destinations'][2],data['destinations'][3]])
                
    if routes: 
           
        fl = []
        for i in range(len(routes)):
            for j in range(len(routes[i])):
                if len(routes[i][j]['locations']) > 1:
                    fl.append(routes[i][j]['locations'])
                    
        
        
        loads = []
        for i in range(len(routes)):
            for j in range(len(routes[i])):
                if len(routes[i][j]['locations']) > 1:
                    loads.append(routes[i][j]['load'])
        
        truck = len(fl)
        fin_res = []
        for i in range(len(fl)):
            if len(fl[i]) == 2:
                orig,dests = fl[i]
                fin_res.append((f"Route {i+1} : {orig} to {dests}  |  Load : {loads[i]}"))
            if len(fl[i]) == 3:
                orig,dests1,dests2 = fl[i]
                fin_res.append((f"Route {i+1} : {orig} to {dests1} to {dests2} |  Load : {loads[i]}"))
            if len(fl[i]) == 4:
                orig,dests1,dests2,dests3 = fl[i]
                fin_res.append((f"Route {i+1} : {orig} to {dests1} to {dests2} to {dests3} |  Load : {loads[i]}"))
            if len(fl[i]) == 5:
                orig,dests1,dests2,dests3,dests4 = fl[i]
                fin_res.append((f"Route {i+1} : {orig} to {dests1} to {dests2} to {dests3} to {dests4} |  Load : {loads[i]}"))
        
        no_truck = f"Number of trucks used : {truck}" 
        if len(re) == 0:      
            if len(fin_res) == 1:
                a0=fin_res[0]
                tr = no_truck
                return render_template('index.html', a0=a0,tr = tr)
            if len(fin_res) == 2:
                a0=fin_res[0]
                a1=fin_res[1]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,tr = tr)
            if len(fin_res) == 3:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,tr = tr)
            if len(fin_res) == 4:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,tr = tr)
            if len(fin_res) == 5:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,tr = tr)
            if len(fin_res) == 6:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                a5=fin_res[5]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,a5=a5,tr = tr)
        if len(re) == 1:
            gm=[]
            for i in range(len(re)):
                if len(re[i]) == 2:
                    gm.append((f"Delivery not feasible from {re[i][0]} to {re[i][1]} due to insufficient inventory level at {re[i][0]}"))
                if len(re[i]) == 3:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]}] due to insufficient inventory level at {re[i][0]}"))
                if len(re[i]) == 4:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]} and {re[i][3]}] due to insufficient inventory level at {re[i][0]}"))   
                if len(re[i]) == 5:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]} and {re[i][3]} and {re[i][4]}] due to insufficient inventory level at {re[i][0]}"))
            b0 = gm[0]
            if len(fin_res) == 1:
                a0=fin_res[0]
                tr = no_truck
                return render_template('index.html', a0=a0,b0=b0,tr = tr)
            if len(fin_res) == 2:
                a0=fin_res[0]
                a1=fin_res[1]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,b0=b0,tr = tr)
            if len(fin_res) == 3:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,b0=b0,tr = tr)
            if len(fin_res) == 4:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,b0=b0,tr = tr)
            if len(fin_res) == 5:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,b0=b0,tr = tr)
            if len(fin_res) == 6:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                a5=fin_res[5]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,a5=a5,b0=b0,tr = tr)
        
        if len(re) == 2:
            gm=[]
            for i in range(len(re)):
                if len(re[i]) == 2:
                    gm.append((f"Delivery not feasible from {re[i][0]} to {re[i][1]} due to insufficient inventory level at {re[i][0]}"))
                if len(re[i]) == 3:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]}] due to insufficient inventory level at {re[i][0]}"))
                if len(re[i]) == 4:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]} and {re[i][3]}] due to insufficient inventory level at {re[i][0]}"))   
                if len(re[i]) == 5:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]} and {re[i][3]} and {re[i][4]}] due to insufficient inventory level at {re[i][0]}"))
            b0 = gm[0]
            b1 = gm[1]
            if len(fin_res) == 1:
                a0=fin_res[0]
                tr = no_truck
                return render_template('index.html', a0=a0,b0=b0,b1=b1,tr = tr)
            if len(fin_res) == 2:
                a0=fin_res[0]
                a1=fin_res[1]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,b0=b0,b1=b1,tr = tr)
            if len(fin_res) == 3:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,b0=b0,b1=b1,tr = tr)
            if len(fin_res) == 4:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,b0=b0,b1=b1,tr = tr)
            if len(fin_res) == 5:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,b0=b0,b1=b1,tr = tr)
            if len(fin_res) == 6:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                a5=fin_res[5]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,a5=a5,b0=b0,b1=b1,tr = tr)  
               
        if len(re) == 3:
            gm=[]
            for i in range(len(re)):
                if len(re[i]) == 2:
                    gm.append((f"Delivery not feasible from {re[i][0]} to {re[i][1]} due to insufficient inventory level at {re[i][0]}"))
                if len(re[i]) == 3:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]}] due to insufficient inventory level at {re[i][0]}"))
                if len(re[i]) == 4:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]} and {re[i][3]}] due to insufficient inventory level at {re[i][0]}"))   
                if len(re[i]) == 5:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]} and {re[i][3]} and {re[i][4]}] due to insufficient inventory level at {re[i][0]}"))
            b0 = gm[0]
            b1 = gm[1]
            b2 = gm[2]
            if len(fin_res) == 1:
                a0=fin_res[0]
                tr = no_truck
                return render_template('index.html', a0=a0,b0=b0,b1=b1,b2=b2,tr = tr)
            if len(fin_res) == 2:
                a0=fin_res[0]
                a1=fin_res[1]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,b0=b0,b1=b1,b2=b2,tr = tr)
            if len(fin_res) == 3:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,b0=b0,b1=b1,b2=b2,tr = tr)
            if len(fin_res) == 4:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,b0=b0,b1=b1,b2=b2,tr = tr)
            if len(fin_res) == 5:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,b0=b0,b1=b1,b2=b2,tr = tr)
            if len(fin_res) == 6:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                a5=fin_res[5]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,a5=a5,b0=b0,b1=b1,b2=b2,tr = tr)     
             

        if len(re) == 4:
            gm=[]
            for i in range(len(re)):
                if len(re[i]) == 2:
                    gm.append((f"Delivery not feasible from {re[i][0]} to {re[i][1]} due to insufficient inventory level at {re[i][0]}"))
                if len(re[i]) == 3:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]}] due to insufficient inventory level at {re[i][0]}"))
                if len(re[i]) == 4:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]} and {re[i][3]}] due to insufficient inventory level at {re[i][0]}"))   
                if len(re[i]) == 5:
                    gm.append((f"Delivery not feasible from {re[i][0]} to [{re[i][1]} and {re[i][2]} and {re[i][3]} and {re[i][4]}] due to insufficient inventory level at {re[i][0]}"))
            b0 = gm[0]
            b1 = gm[1]
            b2 = gm[2]
            b3 = gm[3]
            if len(fin_res) == 1:
                a0=fin_res[0]
                tr = no_truck
                return render_template('index.html', a0=a0,b0=b0,b1=b1,b2=b2,b3=b3,tr = tr)
            if len(fin_res) == 2:
                a0=fin_res[0]
                a1=fin_res[1]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,b0=b0,b1=b1,b2=b2,b3=b3,tr = tr)
            if len(fin_res) == 3:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,b0=b0,b1=b1,b2=b2,b3=b3,tr = tr)
            if len(fin_res) == 4:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,b0=b0,b1=b1,b2=b2,b3=b3,tr = tr)
            if len(fin_res) == 5:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,b0=b0,b1=b1,b2=b2,b3=b3,tr = tr)
            if len(fin_res) == 6:
                a0=fin_res[0]
                a1=fin_res[1]
                a2=fin_res[2]
                a3=fin_res[3]
                a4=fin_res[4]
                a5=fin_res[5]
                tr = no_truck
                return render_template('index.html', a0=a0,a1=a1,a2=a2,a3=a3,a4=a4,a5=a5,b0=b0,b1=b1,b2=b2,b3=b3,tr = tr)     
    
              
        
            
if __name__ == '__main__':
    app.run(debug=True)
