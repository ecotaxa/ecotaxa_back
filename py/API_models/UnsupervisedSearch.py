# moilerat for Lovnower 23-12-2023
# first version of unsupervised search :
# - nearest neighbor with loop in the interface
# - still wip : refer to Clickup task 23-12-2023


# EnumeratedObjectSet

from BO.ObjectSet import EnumeratedObjectSet

import numpy as np
from sklearn.neighbors import NearestNeighbors
from API_models.objects import (
    ObjectSetQueryRsp
)

def rechercher_plus_proche_voisin(np_deep_features_seed, np_deep_features_all):
    # Créer un objet NearestNeighbors avec un seul voisin (le plus proche)
    neigh = NearestNeighbors(n_neighbors=1, algorithm='auto', metric='euclidean')

    # Ajuster (faire le fit) cet objet aux données de "all" pour pouvoir faire des requêtes ensuite
    neigh.fit(np_deep_features_all)

    # Trouver le plus proche voisin dans "all" pour chaque point dans "seed"
    distances, indices = neigh.kneighbors(np_deep_features_seed)

    # distances contient les distances euclidiennes jusqu'au plus proche voisin
    # indices contient les indices de ces voisins dans np_deep_features_all

    distances = np.linalg.norm(np_deep_features_all - np_deep_features_seed, axis=1)
    dist_and_indices = zip(distances, range(len(distances)))
    dist_and_indices = sorted(dist_and_indices, key=lambda x: x[0])


    return dist_and_indices

def test_integration_nn(project_id,
                        seed_object_id = "",
                        source_project_ids = "",
                        features = [],
                        use_scn = False,
                        filters = [],
                        ro_session = None,
                        list_object_ids_from_proj = [],
                        rest_of_data_maybe_needed = None):
    print("Here I am in my sandbox !")
    print(" project_id : " + str(project_id))
    print(" seed_object_id : " + str(seed_object_id))
    list_object_ids = [239072345,
    239072344,
    239072165,
    239072343,
    239072342]

    from DB.CNNFeature import ObjectCNNFeature
    obj = ObjectCNNFeature()
    # Seed object is a special case, it's not a filter but a target
    try:
        seed_object_id = filters.seed_object_id
    except Exception as e:
        print(str(e))
    obj_ids = [int(seed_object_id.lstrip("I"))]

    from BO.Prediction import DeepFeatures
    try:
        np_deep_features_seed = DeepFeatures.np_read_for_objects(ro_session, obj_ids)
        print(np_deep_features_seed)

        np_deep_features_all = DeepFeatures.np_read_for_objects(ro_session, list_object_ids_from_proj)

        print(np_deep_features_all.shape)
        dist_and_indices = rechercher_plus_proche_voisin(np_deep_features_seed, np_deep_features_all)

        print(id)

    except Exception as e:
        print(str(e))

    list_object_ids = [239072345,
                                        239072344,
                                        239072165,
                                        239072343,
                                        239072342]
    object_set: EnumeratedObjectSet = EnumeratedObjectSet(ro_session, list_object_ids)

      # VR 23-12-23 : peut-etre à dupliquer sinon à debugguer au minimum
      # object_set.get_projects_ids

    ids = []
    details = []
    total = 0
    objid: int
    acquisid: int
    sampleid: int
      # for objid, acquisid, sampleid, total, *extra in object_set:
      # ids.append((objid, acquisid, sampleid, proj_id))
      # details.append(extra)

    rsp = ObjectSetQueryRsp()

#    rsp.object_ids = [with_p[0] for with_p in obj_with_parents]
#    rsp.total_ids = total
#    rsp.acquisition_ids = [with_p[1] for with_p in obj_with_parents]
#    rsp.sample_ids = [with_p[2] for with_p in obj_with_parents]
#    rsp.project_ids = [with_p[3] for with_p in obj_with_parents]
#    rsp.details = details

    reordered_indices = list(map(lambda x: x[1], dist_and_indices))
    if rest_of_data_maybe_needed != None:
        for oid_idx_input in reordered_indices:
            # tout d'abord on recherche l'index de l'oid dans la liste des oid de rest_of_data_maybe_needed
            rsp.object_ids.append(rest_of_data_maybe_needed.object_ids[oid_idx_input])
            rsp.acquisition_ids.append(rest_of_data_maybe_needed.acquisition_ids[oid_idx_input])
            rsp.sample_ids.append(rest_of_data_maybe_needed.sample_ids[oid_idx_input])
            rsp.project_ids.append(rest_of_data_maybe_needed.project_ids[oid_idx_input])
            rsp.details.append(rest_of_data_maybe_needed.details[oid_idx_input])
    # rsp.total_ids wtf ??

    return rsp


