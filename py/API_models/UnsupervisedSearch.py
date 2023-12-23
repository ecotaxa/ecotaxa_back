# moilerat for Lovnower 23-12-2023
# first version of unsupervised search :
# - nearest neighbor with loop in the interface
# - still wip : refer to Clickup task 23-12-2023


import numpy as np
from API_models.objects import (
    ObjectSetQueryRsp
)

def sim_search_internal(np_deep_features_seed, np_deep_features_all):

    distances = np.linalg.norm(np_deep_features_all - np_deep_features_seed, axis=1)
    dist_and_indices = zip(distances, range(len(distances)))
    dist_and_indices = sorted(dist_and_indices, key=lambda x: x[0])

    return dist_and_indices

def similarity_search_nn(project_id,
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

    from BO.Prediction import DeepFeatures
    try:
        obj_ids = [int(seed_object_id.lstrip("I"))]
        np_deep_features_seed = DeepFeatures.np_read_for_objects(ro_session, obj_ids)
        print(np_deep_features_seed)

        np_deep_features_all = DeepFeatures.np_read_for_objects(ro_session, list_object_ids_from_proj)

        print(np_deep_features_all.shape)
        dist_and_indices = sim_search_internal(np_deep_features_seed, np_deep_features_all)

        print(id)

    except Exception as e:
        print(str(e))

    rsp = ObjectSetQueryRsp()

    reordered_indices = list(map(lambda x: x[1], dist_and_indices))
    if rest_of_data_maybe_needed != None:
        for oid_idx_input in reordered_indices:
            # tout d'abord on recherche l'index de l'oid dans la liste des oid de rest_of_data_maybe_needed
            rsp.object_ids.append(rest_of_data_maybe_needed.object_ids[oid_idx_input])
            rsp.acquisition_ids.append(rest_of_data_maybe_needed.acquisition_ids[oid_idx_input])
            rsp.sample_ids.append(rest_of_data_maybe_needed.sample_ids[oid_idx_input])
            rsp.project_ids.append(rest_of_data_maybe_needed.project_ids[oid_idx_input])
            rsp.details.append(rest_of_data_maybe_needed.details[oid_idx_input])

    return rsp


