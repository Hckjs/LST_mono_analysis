OUTDIR = build

SIM_VERSION= cta-prod5-paranal_desert-2147m-Paranal-dark_merged

OBSDIR = /home/jonas/aktuell/workb/dvr_test/data/crab/DL1/lpws
SIMDIR = /home/jonas/aktuell/workb/dvr_test/data/mc/prod5/ctapipe


AICT_CONFIG = config/cta_full_config.yaml
AICT_CONFIG_TRAIN = config/cta_full_config_train.yaml
STAGE1_CONFIG = config/stage1_config.json


GAMMA_FILE = gamma_20deg_0deg___$(SIM_VERSION)
GAMMA_DIFFUSE_FILE = gamma_diffuse_20deg_0deg___$(SIM_VERSION)
PROTON_FILE = proton_20deg_0deg___$(SIM_VERSION)
#ELECTRON_FILE = electron_20deg_0deg___$(SIM_VERSION)


CRAB_RUNS=2924

CRAB_DL2=$(addsuffix .h5, $(addprefix $(OUTDIR)/dl2_LST-1.Run0, $(CRAB_RUNS)))
CRAB_DL2_DVR=$(addsuffix .h5, $(addprefix $(OUTDIR)/dl2_dvr_LST-1.Run0, $(CRAB_RUNS)))



all: $(OUTDIR)/cv_separation.h5 \
	$(OUTDIR)/cv_disp.h5 \
	$(OUTDIR)/cv_regressor.h5 \
	$(OUTDIR)/regressor_plots.pdf \
	$(OUTDIR)/disp_plots.pdf \
	$(OUTDIR)/separator_plots.pdf \
	$(CRAB_DL2_DVR) \
	$(CRAB_DL2) \
    $(OUTDIR)/crab_theta2.pdf \
    $(OUTDIR)/crab_theta2_dvr.pdf
#	$(OUTDIR)/dl2_$(GAMMA_FILE)_testing.h5 \
#	$(OUTDIR)/dl2_$(GAMMA_DIFFUSE_FILE)_testing.h5 \
#	$(OUTDIR)/dl2_$(PROTON_FILE)_testing.h5 \
#   $(OUTDIR)/dl2_$(ELECTRON_FILE)_testing.h5 \
#   $(OUTDIR)/pyirf.fits.gz \

#precuts
$(OUTDIR)/%_precuts.h5: $(SIMDIR)/%.h5 $(AICT_CONFIG_TRAIN) | $(OUTDIR)
	aict_apply_cuts \
		$(AICT_CONFIG_TRAIN) \
		$< \
		$@

$(OUTDIR)/dl1_%_testing.h5: $(SIMDIR)/dl1_%_testing.h5 | $(OUTDIR)
	cp \
		$< \
		$@

#train models
$(OUTDIR)/separator.pkl $(OUTDIR)/cv_separation.h5: $(AICT_CONFIG_TRAIN) $(OUTDIR)/dl1_$(PROTON_FILE)_training_precuts.h5 | $(OUTDIR)
$(OUTDIR)/separator.pkl $(OUTDIR)/cv_separation.h5: $(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 | $(OUTDIR)
	aict_train_separation_model \
		$(AICT_CONFIG_TRAIN) \
		$(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 \
		$(OUTDIR)/dl1_$(PROTON_FILE)_training_precuts.h5 \
		$(OUTDIR)/cv_separation.h5 \
		$(OUTDIR)/separator.pkl

$(OUTDIR)/disp.pkl $(OUTDIR)/sign.pkl $(OUTDIR)/cv_disp.h5: $(AICT_CONFIG_TRAIN) $(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 | $(OUTDIR)
	aict_train_disp_regressor \
		$(AICT_CONFIG_TRAIN) \
		$(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 \
		$(OUTDIR)/cv_disp.h5 \
		$(OUTDIR)/disp.pkl \
		$(OUTDIR)/sign.pkl

$(OUTDIR)/regressor.pkl $(OUTDIR)/cv_regressor.h5: $(AICT_CONFIG_TRAIN) $(OUTDIR)/dl1_$(GAMMA_FILE)_training_precuts.h5 | $(OUTDIR)
	aict_train_energy_regressor \
		$(AICT_CONFIG_TRAIN) \
		$(OUTDIR)/dl1_$(GAMMA_FILE)_training_precuts.h5 \
		$(OUTDIR)/cv_regressor.h5 \
		$(OUTDIR)/regressor.pkl

#apply models
$(OUTDIR)/dl2_%.h5: $(OBSDIR)/dl1_%.h5 $(OUTDIR)/separator.pkl $(OUTDIR)/disp.pkl $(OUTDIR)/regressor.pkl $(AICT_CONFIG) add_coords.py | $(OUTDIR)
	aict_apply_cuts \
		$(AICT_CONFIG) \
		$< \
		$(OUTDIR)/tempfile.h5 \
		--chunksize=100000

	aict_apply_separation_model \
		$(AICT_CONFIG) \
		$(OUTDIR)/tempfile.h5 \
		$(OUTDIR)/separator.pkl \
		--chunksize=100000

	aict_apply_disp_regressor \
		$(AICT_CONFIG) \
		$(OUTDIR)/tempfile.h5 \
		$(OUTDIR)/disp.pkl \
		$(OUTDIR)/sign.pkl \
		--chunksize=100000

	aict_apply_energy_regressor \
		$(AICT_CONFIG) \
		$(OUTDIR)/tempfile.h5 \
		$(OUTDIR)/regressor.pkl \
		--chunksize=100000

	python add_coords.py \
		$(OUTDIR)/tempfile.h5

	ptrepack \
		$(OUTDIR)/tempfile.h5 \
		$@ \
		--keep-source-filters

	rm -f $(OUTDIR)/tempfile.h5

#performance plots
$(OUTDIR)/regressor_plots.pdf: $(AICT_CONFIG_TRAIN) $(OUTDIR)/cv_regressor.h5 | $(OUTDIR)
	aict_plot_regressor_performance \
		$(AICT_CONFIG_TRAIN) \
		$(OUTDIR)/cv_regressor.h5 \
		$(OUTDIR)/regressor.pkl \
		-o $@

$(OUTDIR)/separator_plots.pdf: $(AICT_CONFIG_TRAIN) $(OUTDIR)/cv_separation.h5 | $(OUTDIR)
	aict_plot_separator_performance \
		$(AICT_CONFIG_TRAIN) \
		$(OUTDIR)/cv_separation.h5 \
		$(OUTDIR)/separator.pkl \
		-o $@

$(OUTDIR)/disp_plots.pdf: $(AICT_CONFIG_TRAIN) $(OUTDIR)/cv_disp.h5 $(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 | $(OUTDIR)
	aict_plot_disp_performance \
		$(AICT_CONFIG_TRAIN) \
		$(OUTDIR)/cv_disp.h5 \
		$(OUTDIR)/dl1_$(GAMMA_DIFFUSE_FILE)_training_precuts.h5 \
		$(OUTDIR)/disp.pkl \
		$(OUTDIR)/sign.pkl \
		-o $@

#observations
$(OUTDIR)/crab_theta2.pdf: theta2_wobble.py plotting.py calculation.py $(CRAB_DL2) | $(OUTDIR)
	python theta2_wobble.py \
		$(OUTDIR)/crab_theta2.pdf \
		$(CRAB_DL2) \
		'Crab' \
		0.04 \
		0.60

$(OUTDIR)/crab_theta2_dvr.pdf: theta2_wobble.py plotting.py calculation.py $(CRAB_DL2_DVR) | $(OUTDIR)
	python theta2_wobble.py \
		$(OUTDIR)/crab_theta2_dvr.pdf \
		$(CRAB_DL2_DVR) \
		'Crab' \
		0.04 \
		0.60

#pyirf sensitivity 
$(OUTDIR)/pyirf.fits.gz: pyirf_sensitivity.py $(OUTDIR)/dl2_$(GAMMA_FILE)_testing.h5 $(OUTDIR)/dl2_$(PROTON_FILE)_testing.h5 $(OUTDIR)/dl2_$(ELECTRON_FILE)_testing.h5 | $(OUTDIR)
	python pyirf_sensitivity.py \
		$(OUTDIR)/dl2_$(GAMMA_FILE)_testing.h5 \
		$(OUTDIR)/dl2_$(PROTON_FILE)_testing.h5 \
		$(OUTDIR)/dl2_$(ELECTRON_FILE)_testing.h5 \
		$(OUTDIR)/pyirf.fits.gz


$(OUTDIR):
	mkdir -p $(OUTDIR)

clean:
	rm -rf $(OUTDIR)


.PHONY: all clean
